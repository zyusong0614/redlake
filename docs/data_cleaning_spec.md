# Data Cleaning Specifications

## 1. Objective
This document describes the standardized data cleaning pipeline implemented in **dbt + BigQuery** to transform raw Reddit JSON data into analysis-ready tables.  
It replaces the originally planned Spark/Dataproc workflow with a lighter-weight, declarative SQL approach to improve efficiency, transparency, and reproducibility.

---

## 2. Input Sources

| Source | Description | Target BigQuery Table |
|---------|--------------|-----------------------|
| `gs://redlake/raw_json/posts/` | Raw Reddit post JSON files exported by the Cloud Function `redditfetcher` | `redlake_dw.reddit_posts_raw` |
| `gs://redlake/raw_json/comments/` | Raw Reddit comment JSON files exported by the same function | `redlake_dw.reddit_comments_raw` |

Each ingestion run corresponds to a batch timestamp (e.g., `posts_2025-10-27_1500`), allowing versioned retrieval and reproducibility.

---

## 3. Cleaning Objectives
The cleaning process ensures that:
1. Data conforms to FAIR R1.2 quality principles (accuracy, consistency, completeness).  
2. Redundant and null records are removed.  
3. Field names and types are standardized for interoperability between posts and comments tables.  
4. Temporal consistency is guaranteed through UTC timestamp normalization.

---

## 4. Transformation Rules

| Category | Operation | SQL Logic | Purpose |
|-----------|------------|-----------|----------|
| **Deduplication** | Remove duplicates from raw tables | `SELECT DISTINCT *` | Prevent double ingestion during repeated runs |
| **Type Standardization** | Cast numeric/text fields | `SAFE_CAST(score AS INT64)` | Avoid schema drift |
| **Timestamp Normalization** | Convert epoch → UTC timestamp | `TIMESTAMP(created_utc)` | Enable time-based analytics |
| **Text Cleaning** | Trim whitespace and normalize casing | `LOWER(TRIM(title))` | Prepare for NLP pre-processing |
| **Null Filtering** | Exclude incomplete records | `WHERE title IS NOT NULL` / `WHERE body IS NOT NULL` | Maintain meaningful observations |
| **Field Alignment** | Unify naming conventions | `author_hash`, `created_at`, `fetched_at` | Support joins between post/comment datasets |

---

## 5. Example dbt SQL: `stg_reddit_comments.sql`

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
