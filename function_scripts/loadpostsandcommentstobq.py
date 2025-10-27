import functions_framework
import os
import hashlib
import json
from datetime import datetime, timezone
from google.cloud import storage, bigquery

# ============== CONFIG ==============
PROJECT_ID = "redlake-474918"
BUCKET_NAME = "redlake"
DATASET_ID = "redlake_dw"

TARGETS = [
    ("raw_json/posts/", "reddit_posts_raw"),
    ("raw_json/comments/", "reddit_comments_raw"),
]

PIPELINE_RUNS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.pipeline_runs"

# ============== HELPERS: GCS ==============
def move_files_to_timestamped_subdir(prefix, timestamp_str):
    """将 prefix 下的顶层 JSON 文件移动到新的时间戳子目录"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    subfolder = os.path.basename(prefix.strip("/"))
    new_folder = f"{prefix.rstrip('/')}/{subfolder}_{timestamp_str}/"
    moved_files = []

    for blob in bucket.list_blobs(prefix=prefix):
        rel_path = blob.name[len(prefix):]
        if "/" in rel_path or not blob.name.endswith(".json"):
            continue

        new_name = f"{new_folder}{os.path.basename(blob.name)}"
        bucket.copy_blob(blob, bucket, new_name)
        blob.delete()
        moved_files.append(f"gs://{BUCKET_NAME}/{new_name}")

    return moved_files


# ============== HELPERS: BigQuery Loading ==============
def load_json_to_bq(uri_list, table_name):
    """批量将 JSON 文件加载到 BigQuery"""
    if not uri_list:
        return

    bq_client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
        write_disposition="WRITE_APPEND"
    )

    print(f"⏳ Loading {len(uri_list)} files → {table_id}")
    load_job = bq_client.load_table_from_uri(uri_list, table_id, job_config=job_config)
    load_job.result()
    print(f"✅ Loaded {len(uri_list)} files into {table_id}")


# ============== HELPERS: Pipeline Run Registry ==============
def compute_checksum(uri_list):
    """计算文件列表的 SHA256 校验和"""
    return hashlib.sha256(json.dumps(sorted(uri_list)).encode()).hexdigest() if uri_list else None


def insert_pipeline_run_entry(run_id, prefix, table, num_files, checksum, status):
    """插入单条 pipeline run 记录"""
    bq_client = bigquery.Client(project=PROJECT_ID)
    entry = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "source_prefix": prefix,
        "bq_target": table,
        "num_files": num_files,
        "checksum": checksum,
        "status": status
    }

    errors = bq_client.insert_rows_json(PIPELINE_RUNS_TABLE, [entry])
    if errors:
        print(f"⚠️ Failed to record pipeline run: {errors}")
    else:
        print(f"📝 Recorded pipeline run: {run_id} ({status})")


def record_pipeline_run_success(run_id, prefix, table, uri_list):
    """记录成功的运行"""
    checksum = compute_checksum(uri_list)
    insert_pipeline_run_entry(
        run_id, prefix, table, len(uri_list), checksum, "SUCCESS"
    )


def record_pipeline_run_error(run_id, prefix, table, error_msg):
    """记录失败的运行"""
    insert_pipeline_run_entry(
        run_id, prefix, table, 0, None, f"ERROR: {error_msg[:200]}"
    )


def record_pipeline_run_no_files(run_id, prefix, table):
    """记录无文件可处理的运行"""
    insert_pipeline_run_entry(
        run_id, prefix, table, 0, None, "NO_FILES"
    )


# ============== MAIN ENTRY: Cloud Function ==============
@functions_framework.http
def gcs_batch_archiver(request):
    """
    Cloud Function: 
      - 移动 raw_json/posts/ 与 comments/ 下的新文件
      - 加载到 BigQuery
      - 记录 pipeline run 元数据
    """
    timestamp_str = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
    report = []

    for prefix, table in TARGETS:
        print(f"📦 Processing {prefix} → {table}")
        try:
            moved_files = move_files_to_timestamped_subdir(prefix, timestamp_str)
            if not moved_files:
                record_pipeline_run_no_files(timestamp_str, prefix, table)
                report.append(f"{prefix}: no files to process")
                continue

            load_json_to_bq(moved_files, table)
            record_pipeline_run_success(timestamp_str, prefix, table, moved_files)
            report.append(f"✅ {prefix}: moved and loaded {len(moved_files)} files")

        except Exception as e:
            print(f"❌ Error in {prefix}: {e}")
            record_pipeline_run_error(timestamp_str, prefix, table, str(e))
            report.append(f"❌ {prefix}: {e}")

    return "\n".join(report), 200
