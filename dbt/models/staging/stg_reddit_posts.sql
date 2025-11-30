with source as (
  select * from {{ source('redlake_dw', 'reddit_posts_raw') }}
),

renamed as (
  select
    post_id,
    subreddit,
    title,
    coalesce(body, '') as body,
    safe_cast(score as int64) as score,
    safe_cast(num_comments as int64) as num_comments,
    author_hash,
    timestamp(created_utc) as created_at,
    timestamp(fetched_at) as fetched_at
  from source
  where title is not null
)

select * from renamed
