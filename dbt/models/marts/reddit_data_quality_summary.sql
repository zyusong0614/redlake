SELECT
  CURRENT_TIMESTAMP() AS report_time,
  COUNT(*) AS total_posts,
  SUM(CASE WHEN title IS NULL THEN 1 ELSE 0 END) AS missing_titles,
  AVG(post_score) AS avg_post_score,
  COUNT(DISTINCT subreddit) AS subreddit_count,
  MAX(created_at) AS latest_post_time
FROM {{ ref('reddit_sentiment_analysis') }}
