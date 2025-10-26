# 🧱 RedLake dbt + Cloud Build FAIR Pipeline Setup

This document describes how to automatically generate the full dbt project structure, configuration, and Cloud Build integration inside a **monorepo** (e.g. `/dbt` subdirectory).

The goal is to create a reproducible, FAIR-compliant data pipeline using **dbt + BigQuery + Cloud Build + Cloud Scheduler**, inside a larger GCP data platform repository.

---

## 🎯 Objective

Create under `/dbt`:
1. A valid **dbt project structure** (`dbt_project.yml`, `profiles.yml`, `/models/...`)
2. A **Cloud Build YAML** for automation
3. Example SQL and YAML model definitions implementing:
   - Process layer (clean, deduplicate, timestamp normalize)
   - Data quality validation (FAIR R1.2)
   - Analysis layer (sentiment score, data lineage)
4. Make the project executable in Cloud Build + BigQuery.

---

## 🧩 Project Structure

```
dbt/
├── dbt_project.yml
├── profiles.yml
├── cloudbuild.yaml
├── models/
│   ├── sources.yml
│   ├── staging/
│   │   ├── stg_reddit_posts.sql
│   │   ├── stg_reddit_comments.sql
│   │   └── schema.yml
│   ├── intermediate/
│   │   └── int_posts_comments_joined.sql
│   └── marts/
│       ├── reddit_sentiment_analysis.sql
│       └── reddit_data_quality_summary.sql
```

---

## ⚙️ File Contents

### 📘 dbt_project.yml
```yaml
name: 'dbt_redlake'
version: '1.0'
profile: 'redlake'

models:
  dbt_redlake:
    staging:
      materialized: table
    intermediate:
      materialized: ephemeral
    marts:
      materialized: view
```

### 📘 profiles.yml
```yaml
redlake:
  target: prod
  outputs:
    prod:
      type: bigquery
      method: oauth
      project: redlake-474918
      dataset: redlake_dw
      threads: 4
      location: US
```

### 📘 models/sources.yml
```yaml
version: 2
sources:
  - name: redlake_dw
    database: redlake-474918
    tables:
      - name: reddit_posts_raw
      - name: reddit_comments_raw
```

### 📘 models/staging/stg_reddit_posts.sql
```sql
SELECT DISTINCT
  post_id,
  LOWER(TRIM(title)) AS title,
  SAFE_CAST(score AS INT64) AS score,
  SAFE_CAST(num_comments AS INT64) AS num_comments,
  author_hash,
  subreddit,
  TIMESTAMP(created_utc) AS created_at,
  TIMESTAMP(fetched_at) AS fetched_at
FROM {{ source('redlake_dw','reddit_posts_raw') }}
WHERE title IS NOT NULL
```

### 📘 models/staging/stg_reddit_comments.sql
```sql
SELECT DISTINCT
  comment_id,
  SAFE_CAST(body AS STRING) AS body,
  SAFE_CAST(score AS INT64) AS score,
  SAFE_CAST(parent_id AS STRING) AS parent_id,
  author_hash,
  subreddit,
  TIMESTAMP(created_utc) AS created_at,
  TIMESTAMP(fetched_at) AS fetched_at
FROM {{ source('redlake_dw','reddit_comments_raw') }}
WHERE body IS NOT NULL
```

### 📘 models/staging/schema.yml
```yaml
version: 2
models:
  - name: stg_reddit_posts
    description: "Cleaned and standardized Reddit posts"
    columns:
      - name: post_id
        tests: [unique, not_null]
      - name: score
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              max_value: 100000

  - name: stg_reddit_comments
    description: "Cleaned and standardized Reddit comments"
    columns:
      - name: comment_id
        tests: [unique, not_null]
      - name: score
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: -10
              max_value: 10000
```

### 📘 models/intermediate/int_posts_comments_joined.sql
```sql
WITH comments AS (
  SELECT
    REGEXP_REPLACE(parent_id, '^t3_', '') AS post_id,
    AVG(score) AS avg_comment_score,
    COUNT(comment_id) AS total_comments
  FROM {{ ref('stg_reddit_comments') }}
  GROUP BY 1
)
SELECT
  p.post_id,
  p.title,
  p.score AS post_score,
  c.avg_comment_score,
  c.total_comments,
  SAFE_DIVIDE(c.total_comments, p.num_comments) AS comment_ratio,
  p.subreddit,
  p.created_at
FROM {{ ref('stg_reddit_posts') }} p
LEFT JOIN comments c USING(post_id)
```

### 📘 models/marts/reddit_sentiment_analysis.sql
```sql
SELECT
  post_id,
  title,
  post_score,
  avg_comment_score,
  subreddit,
  created_at,
  CASE WHEN post_score >= 0 THEN 0.5 ELSE -0.5 END AS sentiment_score
FROM {{ ref('int_posts_comments_joined') }}
```

### 📘 models/marts/reddit_data_quality_summary.sql
```sql
SELECT
  CURRENT_TIMESTAMP() AS report_time,
  COUNT(*) AS total_posts,
  SUM(CASE WHEN title IS NULL THEN 1 ELSE 0 END) AS missing_titles,
  AVG(post_score) AS avg_post_score,
  COUNT(DISTINCT subreddit) AS subreddit_count,
  MAX(created_at) AS latest_post_time
FROM {{ ref('reddit_sentiment_analysis') }}
```

### 📘 cloudbuild.yaml
```yaml
substitutions:
  _DBT_DOCS_BUCKET: redlake-dbt-docs

steps:
  - name: python:3.11
    entrypoint: bash
    args:
      - -c
      - |
        pip install dbt-bigquery dbt-expectations
        cd dbt
        dbt deps
        dbt run
        dbt test
        dbt docs generate
        gsutil -m rsync -r target/ gs://${_DBT_DOCS_BUCKET}/
timeout: 1800s
```

---

## 🚀 Deployment Guide

1. Push this repo to GitHub.
2. Go to **GCP Console → Cloud Build → Triggers → Connect Repository**.
3. Choose this repository, select branch `main`, and point to `dbt/cloudbuild.yaml`.
4. Give the Cloud Build service account:
   - `roles/bigquery.dataEditor`
   - `roles/storage.admin`
5. (Optional) Add Cloud Scheduler job:
   ```bash
   gcloud scheduler jobs create http run-dbt      --schedule="0 6 * * *"      --uri="https://cloudbuild.googleapis.com/v1/projects/redlake-474918/triggers/dbt_pipeline_trigger:run"      --oidc-service-account-email="redlake-scheduler@redlake-474918.iam.gserviceaccount.com"
   ```

---

## 🧠 FAIR Principle Mapping

| FAIR Principle | Achieved By |
|----------------|--------------|
| **Findable** | dbt docs hosted on GCS |
| **Accessible** | BigQuery datasets + docs |
| **Interoperable** | SQL + YAML schema |
| **Reusable** | Git + Cloud Build reproducibility |
