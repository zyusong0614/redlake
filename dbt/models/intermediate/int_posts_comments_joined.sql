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
