SELECT DISTINCT
  comment_id,
  SAFE_CAST(body AS STRING) AS body,
  SAFE_CAST(score AS INT64) AS score,
  SAFE_CAST(post_id AS STRING) AS post_id,
  author_hash,
  TIMESTAMP(created_utc) AS created_at,
  TIMESTAMP(fetched_at) AS fetched_at
FROM {{ source('redlake_dw','reddit_comments_raw') }}
WHERE body IS NOT NULL
