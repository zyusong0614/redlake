WITH comments AS (
  SELECT
    post_id AS post_id,
    AVG(score) AS avg_comment_score,
    AVG(sentiment_score) AS avg_comment_sentiment,
    COUNT(comment_id) AS total_comments
  FROM {{ ref('stg_reddit_comments') }}
  GROUP BY 1
)
SELECT
  p.post_id,
  p.title,
  p.body,
  p.score AS post_score,
  p.sentiment_score AS post_sentiment_score,
  p.num_comments,
  p.fetched_at,
  c.avg_comment_score,
  c.avg_comment_sentiment,
  c.total_comments,
  SAFE_DIVIDE(c.total_comments, p.num_comments) AS comment_ratio,
  p.subreddit,
  p.created_at
FROM {{ ref('stg_reddit_posts') }} p
LEFT JOIN comments c USING(post_id)
