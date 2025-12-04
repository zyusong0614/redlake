# RedLake – Reproducible GCP Deployment Guide

## Repository Structure (High‑Level)

- `README_GCP_DEPLOYMENT.md` – This deployment guide for reproducing the pipeline in your own GCP project.
- `RedLake_dbt_CloudBuild_FAIR_Pipeline_Setup.md` – Original technical design and setup notes for the RedLake FAIR pipeline.
- `function_scripts/` – Cloud Function source:
  - `redditfetcherpr.py` – Reddit data acquisition, anonymization, sentiment, and upload to GCS.
  - `loadpostsandcommentstobq.py` – Batch loader that moves raw JSON in GCS and loads it into BigQuery tables.
  - `subreddit.csv` – Example list of subreddits to monitor.
- `dbt/` – dbt project (models, seeds, configs, and `cloudbuild.yaml` for CI/CD of transformations and docs).
- `dataset/` – Example exported tables / views representing different logical layers (staging, intermediate, marts).
- `docs/` – FAIR, GDPR, and data‑management documentation (e.g., anonymization procedure, compliance framework).
- `archi_graph/` – Architecture and design diagrams (Excalidraw files and PNGs).
- `local_test/` – Local notebooks and test assets (not part of the production pipeline).

This guide explains how a new user can **reproduce** a RedLake‑style pipeline in **their own** GCP project (no access to your original project required).

It covers:
- Getting Reddit API credentials
- Creating GCS buckets and folder structure
- Creating BigQuery dataset and tables (with schemas)
- Deploying the two Cloud Functions
- Setting up dbt + Cloud Build for transformations and FAIR docs

You can rename resources as you like, but keep them consistent across steps.

---

## 1. Prerequisites

- A Google Cloud project (call it `YOUR_GCP_PROJECT_ID`)
- Billing enabled on that project
- Google Cloud SDK (`gcloud`) installed locally
- Python 3.11+ installed locally
- Basic familiarity with:
  - Google Cloud Console
  - BigQuery
  - Cloud Functions (2nd gen) or Cloud Run
  - Cloud Storage

---

## 2. Reddit API Credentials

1. Go to Reddit: https://www.reddit.com/prefs/apps
2. Click **“create another app…”**
3. Set:
   - **name**: `RedLakeBot` (or any)
   - **type**: **script**
   - **redirect uri**: `http://localhost:8080` (not used in this pipeline but required)
4. After creation you will see:
   - **client id** (a short string under the app name)
   - **client secret**
5. Save these values; you will configure them as environment variables for the Cloud Function:
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`

---

## 3. GCS Bucket and Folder Structure

### 3.1 Create a Bucket

Choose a global unique bucket name, for example:

- `YOUR_BUCKET_NAME = redlake-demo-raw`

Create the bucket:

```bash
gcloud storage buckets create gs://YOUR_BUCKET_NAME \
  --project=YOUR_GCP_PROJECT_ID \
  --location=US
```

### 3.2 Required Folder Layout

The pipeline expects these prefixes:

- Raw Reddit JSON:
  - `gs://YOUR_BUCKET_NAME/raw_json/posts/`
  - `gs://YOUR_BUCKET_NAME/raw_json/comments/`
- NLTK models for VADER (sentiment):
  - `gs://YOUR_BUCKET_NAME/models/nltk_data/...`

You do **not** need to create folders manually; they will appear when you upload files. Just keep these paths consistent with the environment variables or hard‑coded values you use in the Cloud Functions.

---

## 4. BigQuery Dataset and Tables

### 4.1 Create Dataset

Use a dataset name, for example:

- `DATASET_ID = redlake_dw`

Create the dataset:

```bash
bq --location=US mk --dataset \
  YOUR_GCP_PROJECT_ID:redlake_dw
```

### 4.2 Tables – Names and Schemas

The pipeline uses:

1. `reddit_posts_raw`
2. `reddit_comments_raw`
3. `pipeline_runs`

#### 4.2.1 `reddit_posts_raw`

Fully qualified:  
`YOUR_GCP_PROJECT_ID.redlake_dw.reddit_posts_raw`

Suggested schema:

- `post_id` (STRING, REQUIRED)
- `title` (STRING, NULLABLE)
- `body` (STRING, NULLABLE)
- `subreddit` (STRING, NULLABLE)
- `author_hash` (STRING, NULLABLE)
- `created_utc` (TIMESTAMP, NULLABLE)
- `score` (INTEGER, NULLABLE)
- `num_comments` (INTEGER, NULLABLE)
- `permalink` (STRING, NULLABLE)
- `sentiment_score` (FLOAT, NULLABLE)
- `fetched_at` (TIMESTAMP, NULLABLE)

Create table:

```bash
bq mk --table YOUR_GCP_PROJECT_ID:redlake_dw.reddit_posts_raw \
post_id:STRING,title:STRING,body:STRING,subreddit:STRING,author_hash:STRING,created_utc:TIMESTAMP,score:INTEGER,num_comments:INTEGER,permalink:STRING,sentiment_score:FLOAT,fetched_at:TIMESTAMP
```

#### 4.2.2 `reddit_comments_raw`

Fully qualified:  
`YOUR_GCP_PROJECT_ID.redlake_dw.reddit_comments_raw`

Suggested schema:

- `comment_id` (STRING, REQUIRED)
- `post_id` (STRING, NULLABLE)
- `body` (STRING, NULLABLE)
- `score` (INTEGER, NULLABLE)
- `author_hash` (STRING, NULLABLE)
- `created_utc` (TIMESTAMP, NULLABLE)
- `sentiment_score` (FLOAT, NULLABLE)
- `fetched_at` (TIMESTAMP, NULLABLE)

Create table:

```bash
bq mk --table YOUR_GCP_PROJECT_ID:redlake_dw.reddit_comments_raw \
comment_id:STRING,post_id:STRING,body:STRING,score:INTEGER,author_hash:STRING,created_utc:TIMESTAMP,sentiment_score:FLOAT,fetched_at:TIMESTAMP
```

#### 4.2.3 `pipeline_runs`

Fully qualified:  
`YOUR_GCP_PROJECT_ID.redlake_dw.pipeline_runs`

Used to track batch loads from GCS to BigQuery.

Suggested schema:

- `run_id` (STRING, REQUIRED) – e.g. timestamp or UUID
- `timestamp` (TIMESTAMP, REQUIRED) – run start time
- `source_prefix` (STRING, REQUIRED) – e.g. `raw_json/posts/`
- `bq_target` (STRING, REQUIRED) – e.g. `reddit_posts_raw`
- `num_files` (INTEGER, NULLABLE)
- `checksum` (STRING, NULLABLE) – SHA‑256 over list of files
- `status` (STRING, REQUIRED) – `SUCCESS`, `NO_FILES`, or `ERROR:...`

Create table:

```bash
bq mk --table YOUR_GCP_PROJECT_ID:redlake_dw.pipeline_runs \
run_id:STRING,timestamp:TIMESTAMP,source_prefix:STRING,bq_target:STRING,num_files:INTEGER,checksum:STRING,status:STRING
```

> Note: The Cloud Function code can also create tables automatically with autodetect schemas, but pre‑creating them makes the deployment fully explicit and reproducible.

---

## 5. Service Account and IAM

Create a dedicated service account, for example:

```bash
gcloud iam service-accounts create redlake-sa \
  --project=YOUR_GCP_PROJECT_ID \
  --display-name="RedLake Pipeline Service Account"
```

Grant roles (least privilege recommendation – you can further tighten later):

```bash
gcloud projects add-iam-policy-binding YOUR_GCP_PROJECT_ID \
  --member="serviceAccount:redlake-sa@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding YOUR_GCP_PROJECT_ID \
  --member="serviceAccount:redlake-sa@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding YOUR_GCP_PROJECT_ID \
  --member="serviceAccount:redlake-sa@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudfunctions.invoker"
```

For Cloud Build, also give:

```bash
gcloud projects add-iam-policy-binding YOUR_GCP_PROJECT_ID \
  --member="serviceAccount:${YOUR_GCP_PROJECT_ID}@cloudbuild.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding YOUR_GCP_PROJECT_ID \
  --member="serviceAccount:${YOUR_GCP_PROJECT_ID}@cloudbuild.gserviceaccount.com" \
  --role="roles/bigquery.admin"
```

---

## 6. Deploy Cloud Function: Reddit Fetcher

This function:
- Calls Reddit API via PRAW
- Anonymizes text using Presidio
- Computes sentiment scores using NLTK VADER
- Writes NDJSON files to:
  - `gs://YOUR_BUCKET_NAME/raw_json/posts/...`
  - `gs://YOUR_BUCKET_NAME/raw_json/comments/...`

### 6.1 Prepare Code

Implementation details (request handling, anonymization, sentiment, upload to GCS) are all in  
`function_scripts/redditfetcherpr.py`. When you package this as a Cloud Function:

- Use `reddit_fetcher` (already defined in that file) as the HTTP entrypoint.
- Install the same Python dependencies as declared in your local environment (e.g. PRAW, NLTK, Presidio, GCS client).

### 6.2 Deploy (2nd Gen Cloud Functions, Python 3.11 – High Level)

In your own project, create an HTTP‑triggered Python 3.11 Cloud Function using the code in  
`function_scripts/redditfetcherpr.py`, and configure:

- A service account with access to GCS.
- Environment variables: `BUCKET_NAME`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`.
- Region, authentication and trigger according to your security requirements (console or `gcloud` UI/CLI flow of your choice).

---

## 7. Deploy Cloud Function: GCS → BigQuery Loader

This function:
- Moves JSON files in:
  - `gs://YOUR_BUCKET_NAME/raw_json/posts/`
  - `gs://YOUR_BUCKET_NAME/raw_json/comments/`
- Into timestamped subdirectories inside those prefixes
- Loads them into `reddit_posts_raw` and `reddit_comments_raw`
- Logs each run in `pipeline_runs`

### 7.1 Prepare Code

All loader logic (moving files, loading to BigQuery, recording pipeline runs) is implemented in  
`function_scripts/loadpostsandcommentstobq.py`. Before deploying, update the constants in that file
(`PROJECT_ID`, `BUCKET_NAME`, `DATASET_ID`) to match your own environment.

The HTTP entrypoint `gcs_batch_archiver` is already defined there and can be used directly when you
create the Cloud Function.

### 7.2 Deploy Function (High Level)

Create another HTTP‑triggered Python 3.11 Cloud Function from `function_scripts/loadpostsandcommentstobq.py`,
using `gcs_batch_archiver` as the entrypoint and the same service account you used for the fetcher.
Ensure this function has permissions to read from `YOUR_BUCKET_NAME` and write to the `redlake_dw` dataset.

### 7.3 Set Up a Scheduler Trigger (Optional)

Optionally configure a **Cloud Scheduler** job (via console or CLI) to call the loader function URL
on a regular schedule (for example, every hour) so that new raw JSON files are periodically moved from
the top‑level prefixes into timestamped subdirectories and loaded into BigQuery.

---

## 8. dbt Project Setup

### 8.1 Local dbt Setup

From the `dbt` directory in this repo (or a cloned copy):

```bash
cd dbt
python -m venv .venv
source .venv/bin/activate
pip install dbt-bigquery dbt-expectations
```

Create or edit your `~/.dbt/profiles.yml`:

```yaml
redlake_profile:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: YOUR_GCP_PROJECT_ID
      dataset: redlake_dw
      threads: 4
      keyfile: /path/to/your/service-account-key.json
      timeout_seconds: 300
```

Update `dbt/dbt_project.yml` to ensure:

```yaml
name: 'dbt_redlake'
version: '1.0.0'
profile: 'redlake_profile'
config-version: 2
```

### 8.2 Run Models and Tests Locally

```bash
cd dbt
dbt deps
dbt run
dbt test
dbt docs generate
```

This will:
- Transform `reddit_posts_raw` / `reddit_comments_raw`
- Build staging, intermediate, and marts models
- Run expectations tests
- Generate documentation under `target/`

---

## 9. Cloud Build Integration (Optional but Recommended)

To make dbt runs automated on every Git push:

### 9.1 Create GCS Bucket for dbt Docs

```bash
gcloud storage buckets create gs://YOUR_DBT_DOCS_BUCKET \
  --project=YOUR_GCP_PROJECT_ID \
  --location=US
```

### 9.2 `cloudbuild.yaml` (Example)

Place `cloudbuild.yaml` at the repo root:

```yaml
substitutions:
  _DBT_DOCS_BUCKET: YOUR_DBT_DOCS_BUCKET

steps:
  - name: gcr.io/cloud-builders/gcloud
    id: "Install dbt & dependencies"
    entrypoint: bash
    args:
      - -c
      - |
        apt-get update && apt-get install -y python3-pip git
        pip3 install --upgrade pip
        pip3 install dbt-bigquery dbt-expectations

  - name: gcr.io/cloud-builders/gcloud
    id: "Run dbt"
    entrypoint: bash
    args:
      - -c
      - |
        cd dbt
        dbt deps
        dbt run
        dbt test
        dbt docs generate

  - name: gcr.io/cloud-builders/gsutil
    id: "Upload docs"
    args:
      - -m
      - rsync
      - -r
      - dbt/target/
      - gs://${_DBT_DOCS_BUCKET}/

timeout: 1800s
options:
  logging: CLOUD_LOGGING_ONLY
```

### 9.3 Cloud Build Trigger

1. In Cloud Console → **Cloud Build** → **Triggers**
2. Create new trigger:
   - Source: your GitHub repo
   - Branch: `main` (or any)
   - Build config: `cloudbuild.yaml`
3. On push to that branch, Cloud Build will:
   - Run dbt models and tests
   - Publish docs to `gs://YOUR_DBT_DOCS_BUCKET`

You can access docs at:

```text
https://storage.googleapis.com/YOUR_DBT_DOCS_BUCKET/index.html
```

---

## 10. End‑to‑End Run Summary

1. **Reddit API setup** → client id & secret
2. **GCS bucket** → `YOUR_BUCKET_NAME` with `raw_json/posts/` and `raw_json/comments/`
3. **BigQuery dataset** → `redlake_dw`
4. **BigQuery tables** → `reddit_posts_raw`, `reddit_comments_raw`, `pipeline_runs`
5. **Service account + IAM** → `redlake-sa` with Storage / BigQuery access
6. **Cloud Function 1** → `reddit-fetcher` writes NDJSON to GCS
7. **Cloud Function 2** → `gcs-batch-archiver` moves + loads files into BigQuery
8. **dbt project** → transforms, tests, and documents the warehouse
9. **Cloud Build (optional)** → automates dbt runs and publishes FAIR docs

Following these steps, a new user can reproduce the RedLake‑style FAIR pipeline entirely inside their own GCP project, without any access to your original environment.
