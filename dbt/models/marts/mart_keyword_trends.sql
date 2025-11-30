with mentions as (
  select * from {{ ref('int_keyword_mentions') }}
)

select
  date(created_at) as report_date,
  keyword,
  category,
  subreddit,
  count(*) as mention_count,
  sum(reddit_score) as total_reddit_score,
  avg(sentiment_score) as avg_sentiment
from mentions
group by 1, 2, 3, 4
order by 1 desc, 5 desc
