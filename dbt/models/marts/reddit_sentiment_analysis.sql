SELECT
  post_id,
  title,
  post_score,
  avg_comment_score,
  subreddit,
  created_at,
  CASE WHEN post_score >= 0 THEN 0.5 ELSE -0.5 END AS sentiment_score
FROM {{ ref('int_posts_comments_joined') }}
