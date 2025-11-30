with posts as (
  select
    post_id as item_id,
    subreddit,
    coalesce(title, '') || ' ' || coalesce(body, '') as content,
    score,
    created_at,
    'post' as type
  from {{ ref('stg_reddit_posts') }}
),

comments as (
  select
    c.comment_id as item_id,
    p.subreddit,
    coalesce(c.body, '') as content,
    c.score,
    c.created_at,
    'comment' as type
  from {{ ref('stg_reddit_comments') }} c
  inner join {{ ref('stg_reddit_posts') }} p
    on c.post_id = p.post_id
),

combined_content as (
  select item_id, subreddit, content, score, created_at, type, lower(content) as lower_content from posts
  union all
  select item_id, subreddit, content, score, created_at, type, lower(content) as lower_content from comments
),

keywords as (
  select * from {{ ref('tech_keywords') }}
)

select
  c.item_id,
  c.created_at,
  c.subreddit,
  c.type,
  c.score as reddit_score,
  k.keyword,
  k.category,
  case
    when c.lower_content like '%good%' or c.lower_content like '%great%' then 1
    when c.lower_content like '%bad%' or c.lower_content like '%hate%' then -1
    else 0
  end as sentiment_score
from combined_content c
inner join keywords k
  on c.lower_content like concat('%', lower(k.keyword), '%')
