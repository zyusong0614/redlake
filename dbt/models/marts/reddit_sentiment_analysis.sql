SELECT
  post_id,
  title,
  body,
  post_score,
  post_sentiment_score,
  num_comments,
  avg_comment_score,
  avg_comment_sentiment,
  subreddit,
  created_at,
  fetched_at
FROM {{ ref('int_posts_comments_joined') }}
