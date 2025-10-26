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
