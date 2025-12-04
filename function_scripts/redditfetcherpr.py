import functions_framework
import praw
import json
import os
import logging
import hashlib
import io
import sys
import types
import zipfile
import concurrent.futures # 👈 新增：并发库
from datetime import datetime, timedelta, timezone
from google.cloud import storage

# ============== FIX: MOCK SQLITE3 FOR NLTK ==============
module_mock = types.ModuleType("sqlite3")
module_mock.connect = lambda *args, **kwargs: None
sys.modules["sqlite3"] = module_mock
sys.modules["sqlite3.dbapi2"] = module_mock
# ========================================================

import nltk 
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

# ============== LOGGING SETUP ==============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("presidio-analyzer").setLevel(logging.WARNING)

# ============== GLOBAL VARS (LAZY LOAD) ==============
_sia = None
_analyzer = None
_anonymizer = None
_reddit = None

# ============== CONFIG ==============
BUCKET_NAME = 'redlake' 
GCS_PREFIX = 'raw_json'
GCS_MODEL_PATH = 'models/nltk_data' 

# ============== HELPER: DOWNLOAD FROM GCS ==============
def download_nltk_from_gcs():
    """从 GCS 下载 NLTK 数据到 /tmp，包含完整性检查"""
    local_base_path = "/tmp/nltk_data"
    target_zip = os.path.join(local_base_path, "sentiment/vader_lexicon.zip")
    
    if os.path.exists(target_zip):
        try:
            if os.path.getsize(target_zip) < 1024: raise ValueError("File too small")
            with zipfile.ZipFile(target_zip, 'r') as zip_ref:
                if zip_ref.testzip() is not None: raise zipfile.BadZipFile("CRC check failed")
            # logger.info("✅ Found valid cached NLTK models.") 
            return local_base_path
        except Exception:
            try: os.remove(target_zip)
            except: pass

    logger.info(f"⬇️ Downloading NLTK models from GCS...")
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = bucket.list_blobs(prefix=GCS_MODEL_PATH)
    found = False
    for blob in blobs:
        if blob.name.endswith('/'): continue 
        relative_path = os.path.relpath(blob.name, GCS_MODEL_PATH)
        local_file_path = os.path.join(local_base_path, relative_path)
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        blob.download_to_filename(local_file_path)
        found = True
            
    if not found:
        logger.error(f"❌ No files found in GCS prefix: {GCS_MODEL_PATH}")
        raise FileNotFoundError("NLTK models not found")
    
    return local_base_path

# ============== LAZY LOADERS ==============
def get_sia():
    global _sia
    if _sia is None:
        try:
            nltk_path = download_nltk_from_gcs()
            nltk.data.path.insert(0, nltk_path)
            _sia = SentimentIntensityAnalyzer()
        except Exception as e:
            logger.error(f"❌ Failed to initialize VADER: {e}")
            raise e
    return _sia

def get_presidio():
    global _analyzer, _anonymizer
    if _analyzer is None:
        _analyzer = AnalyzerEngine() 
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer

def get_reddit():
    global _reddit
    if _reddit is None:
        client_id = os.environ.get("REDDIT_CLIENT_ID")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        if client_id and client_secret:
            _reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent="RedLakeBot/0.9 (Parallel)"
            )
    return _reddit

# ============== WORKER FUNCTIONS ==============
def sha256_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def get_vader_score(text):
    if not text: return 0.0
    try: return get_sia().polarity_scores(text)['compound']
    except: return 0.0

def clean_text_with_presidio(text):
    if not text: return ""
    try:
        analyzer_instance, anonymizer_instance = get_presidio()
        results = analyzer_instance.analyze(text=text, language="en")
        if not results: return text
        return anonymizer_instance.anonymize(text=text, analyzer_results=results).text
    except Exception as e:
        logger.warning(f"⚠️ Presidio error: {e}")
        return text

def process_single_post(post):
    """
    [新增] 单个帖子的处理逻辑，用于线程池并发执行
    """
    try:
        # 1. 基础过滤
        if post.selftext and post.selftext.strip().lower() in {"[removed]", "[deleted]"}:
            return None, None

        post_dt = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
        
        # 2. NLP 处理 (CPU 密集)
        clean_title = clean_text_with_presidio(post.title)
        clean_body = clean_text_with_presidio(post.selftext)
        full_text = f"{clean_title} . {clean_body}"
        sentiment_score = get_vader_score(full_text)

        post_data = {
            'post_id': post.id,
            'title': clean_title,
            'body': clean_body,
            'subreddit': post.subreddit.display_name,
            'author_hash': sha256_hash(str(post.author)) if post.author else None,
            'created_utc': post_dt.isoformat(),
            'score': post.score,
            'num_comments': post.num_comments,
            'permalink': post.permalink,
            'sentiment_score': sentiment_score,
            'fetched_at': datetime.utcnow().isoformat()
        }

        # 3. 评论抓取 (网络 I/O 密集)
        comments_data = []
        try:
            # 网络请求
            post.comments.replace_more(limit=0)
            
            for comment in post.comments.list()[:5]:
                if not comment.body or comment.body in {"[removed]", "[deleted]"}: continue
                
                clean_c_body = clean_text_with_presidio(comment.body)
                c_sentiment = get_vader_score(clean_c_body)

                comments_data.append({
                    'comment_id': comment.id,
                    'post_id': post.id,
                    'body': clean_c_body,
                    'score': comment.score,
                    'author_hash': sha256_hash(str(comment.author)) if comment.author else None,
                    'created_utc': datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).isoformat(),
                    'sentiment_score': c_sentiment,
                    'fetched_at': datetime.utcnow().isoformat()
                })
        except Exception:
            pass 

        return post_data, comments_data

    except Exception as e:
        logger.error(f"❌ Worker Error {post.id}: {e}")
        return None, None

def upload_ndjson_to_gcs(posts, comments):
    logger.info(f"Uploading {len(posts)} posts and {len(comments)} comments...")
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    now = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
    
    p_name = f"{GCS_PREFIX}/posts/posts_{now}.json"
    c_name = f"{GCS_PREFIX}/comments/comments_{now}.json"

    p_buff = io.StringIO()
    for p in posts: p_buff.write(json.dumps(p) + "\n")
    bucket.blob(p_name).upload_from_string(p_buff.getvalue(), content_type="application/x-ndjson")

    c_buff = io.StringIO()
    for c in comments: c_buff.write(json.dumps(c) + "\n")
    bucket.blob(c_name).upload_from_string(c_buff.getvalue(), content_type="application/x-ndjson")

    return p_name, c_name

# ============== CORE FETCH LOGIC (PARALLEL) ==============
def fetch_posts_bulk(subreddit_name, limit=100, time_filter='year'):
    logger.info(f"🚀 Bulk Fetching: r/{subreddit_name} | Limit: {limit} | Filter: {time_filter}")
    
    posts = []
    comments = []
    min_date = None
    max_date = None
    
    reddit_client = get_reddit()
    if not reddit_client: return [], [], None, None

    try:
        subreddit = reddit_client.subreddit(subreddit_name)
        
        # 1. 快速获取帖子列表
        candidate_posts = list(subreddit.top(time_filter=time_filter, limit=limit))
        logger.info(f"📋 Found {len(candidate_posts)} candidates. Starting ThreadPool...")

        # 2. 并行处理 (使用 8 个线程)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_post = {executor.submit(process_single_post, p): p for p in candidate_posts}
            
            count = 0
            for future in concurrent.futures.as_completed(future_to_post):
                count += 1
                if count % 10 == 0: logger.info(f"⚡ Parallel Progress: {count}/{len(candidate_posts)}")
                
                try:
                    p_data, c_data_list = future.result()
                    if p_data:
                        # 统计日期
                        p_date = datetime.fromisoformat(p_data['created_utc'])
                        if min_date is None or p_date < min_date: min_date = p_date
                        if max_date is None or p_date > max_date: max_date = p_date
                        
                        posts.append(p_data)
                        comments.extend(c_data_list)
                except Exception as exc:
                    logger.error(f"Thread Exception: {exc}")

    except Exception as e:
        logger.error(f"❌ PRAW Error: {e}")
    
    min_str = min_date.strftime('%Y-%m-%d') if min_date else "N/A"
    max_str = max_date.strftime('%Y-%m-%d') if max_date else "N/A"

    logger.info(f"✅ Collection Complete. {len(posts)} posts. Range: {min_str} to {max_str}")
    return posts, comments, min_str, max_str

# ============== ENTRYPOINT ==============
@functions_framework.http
def reddit_fetcher(request):
    try:
        req_json = request.get_json(silent=True)
        req_args = request.args
        def get_p(k, d): 
            if req_json and k in req_json: return req_json[k]
            return req_args.get(k, d)

        sub = get_p('subreddit', 'technology')
        lim = int(get_p('limit', 100))
        tf = get_p('time_filter', 'year')
        ingestion_date = datetime.utcnow().strftime("%Y-%m-%d")

        logger.info(f"📥 Start: r/{sub} | Limit: {lim}")

        if not get_reddit(): return "Server Error: Reddit client failed.", 500

        posts, comments, d_start, d_end = fetch_posts_bulk(sub, lim, tf)

        if not posts: return f"No posts found in r/{sub}", 200

        p_file, c_file = upload_ndjson_to_gcs(posts, comments)

        return json.dumps({
            "status": "success",
            "ingestion_date": ingestion_date,
            "data_range": f"{d_start} to {d_end}",
            "posts_count": len(posts),
            "comments_count": len(comments),
            "posts_file": f"gs://{BUCKET_NAME}/{p_file}",
            "comments_file": f"gs://{BUCKET_NAME}/{c_file}"
        }), 200, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.exception(f"❌ Server Error: {e}")
        return f"Server Error: {str(e)}", 500