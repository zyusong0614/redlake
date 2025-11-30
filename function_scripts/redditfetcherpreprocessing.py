import functions_framework
import praw
import json
import os
import logging
from datetime import datetime, timezone
import hashlib
from google.cloud import storage
import io

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

# ============== LOGGING SETUP ==============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============== PRESIDIO INIT ==============
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# ============== CONFIG ==============
BUCKET_NAME = 'redlake'
GCS_PREFIX = 'raw_json'

KEYWORDS = {
    "automate", "startup", "idea", "problem", "solution",
    "opportunity", "pain", "build", "app", "tool", "fix",
    "manual", "slow", "market", "ux", "frustrating", "extension"
}

# ============== REDDIT CLIENT ==============
logger.info("Initializing Reddit client.")
reddit = praw.Reddit(
    client_id=os.environ.get("REDDIT_CLIENT_ID"),
    client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
    user_agent="RedLakeBot/0.3 (academic research by u/YOUR_USERNAME, CS598 UIUC)"
)

# ============== HELPERS ==============
def sha256_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def clean_text_with_presidio(text):
    if not text:
        return text
    try:
        results = analyzer.analyze(text=text, language="en")
        if not results:
            return text
        anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text
    except Exception as e:
        logger.warning(f"Presidio anonymization failed: {e}")
        return text

def upload_ndjson_to_gcs(posts, comments):
    logger.info("Uploading data to GCS...")

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    now = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")

    posts_filename = f"{GCS_PREFIX}/posts/posts_{now}.json"
    comments_filename = f"{GCS_PREFIX}/comments/comments_{now}.json"

    # Upload posts
    post_buffer = io.StringIO()
    for post in posts:
        post_buffer.write(json.dumps(post) + "\n")
    bucket.blob(posts_filename).upload_from_string(
        post_buffer.getvalue(), content_type="application/json"
    )
    logger.info(f"Uploaded {len(posts)} posts → gs://{BUCKET_NAME}/{posts_filename}")

    # Upload comments
    comment_buffer = io.StringIO()
    for comment in comments:
        comment_buffer.write(json.dumps(comment) + "\n")
    bucket.blob(comments_filename).upload_from_string(
        comment_buffer.getvalue(), content_type="application/json"
    )
    logger.info(f"Uploaded {len(comments)} comments → gs://{BUCKET_NAME}/{comments_filename}")

    return posts_filename, comments_filename

# ============== FETCH POSTS ==============
def fetch_posts_with_comments(subreddit_name, limit=10):
    logger.info(f"Fetching posts from r/{subreddit_name} (limit={limit})")
    posts, comments = [], []

    try:
        subreddit = reddit.subreddit(subreddit_name)
        for post in subreddit.rising(limit=limit):
            logger.debug(f"Checking post: {post.id} - {post.title[:50]}")

            if not post.selftext or post.selftext.strip().lower() in {"[removed]", "[deleted]"}:
                logger.info(f"Skipped post {post.id} (removed or deleted)")
                continue

            clean_title = clean_text_with_presidio(post.title)
            clean_body = clean_text_with_presidio(post.selftext)

            post_data = {
                'post_id': post.id,
                'title': clean_title,
                'body': clean_body,
                'subreddit': post.subreddit.display_name,
                'author_hash': sha256_hash(str(post.author)) if post.author else None,
                'created_utc': datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                'score': post.score,
                'num_comments': post.num_comments,
                'permalink': post.permalink,
                'fetched_at': datetime.utcnow().isoformat()
            }
            posts.append(post_data)
            logger.info(f"✅ Added post {post.id} | score={post.score}, comments={post.num_comments}")

            try:
                post.comments.replace_more(limit=0)
                for comment in post.comments.list()[:5]:
                    if not comment.body or comment.body.strip().lower() in {"[removed]", "[deleted]"}:
                        logger.debug(f"Skipped comment {comment.id} (removed or deleted)")
                        continue

                    clean_comment = clean_text_with_presidio(comment.body)
                    comments.append({
                        'comment_id': comment.id,
                        'post_id': post.id,
                        'body': clean_comment,
                        'author_hash': sha256_hash(str(comment.author)) if comment.author else None,
                        'created_utc': datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).isoformat(),
                        'score': comment.score,
                        'fetched_at': datetime.utcnow().isoformat()
                    })
                logger.info(f"🗨️  Fetched comments for post {post.id} ({len(comments)} total comments so far)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch comments for post {post.id}: {e}")

    except Exception as e:
        logger.error(f"Failed to fetch posts: {e}")

    logger.info(f"Fetch complete: {len(posts)} posts and {len(comments)} comments collected.")
    return posts, comments

# ============== CLOUD FUNCTION ENTRYPOINT ==============
@functions_framework.http
def reddit_fetcher_2(request):
    logger.info("🔄 Cloud Function triggered")

    try:
        subreddit = request.args.get("subreddit", "technology")
        limit = int(request.args.get("limit", 20))
        logger.info(f"📥 Parameters: subreddit={subreddit}, limit={limit}")

        posts, comments = fetch_posts_with_comments(subreddit, limit)

        if not posts:
            logger.warning(f"No posts fetched from r/{subreddit}")
            return f"No posts fetched from r/{subreddit}.", 200

        posts_file, comments_file = upload_ndjson_to_gcs(posts, comments)

        logger.info("✅ Function completed successfully.")
        return (
            f"✅ Uploaded {len(posts)} posts and {len(comments)} comments from r/{subreddit}\n"
            f"🗂 Posts: gs://{BUCKET_NAME}/{posts_file}\n"
            f"💬 Comments: gs://{BUCKET_NAME}/{comments_file}",
            200,
        )

    except Exception as e:
        logger.exception(f"❌ Server Error: {e}")
        return f"Server Error: {str(e)}", 500
