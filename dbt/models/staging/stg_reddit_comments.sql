with source as (
  select * from {{ source('redlake_dw', 'reddit_comments_raw') }}
),

renamed as (
  select
    comment_id,
    safe_cast(body as string) as body,
    safe_cast(score as int64) as score,
    safe_cast(post_id as string) as post_id,
    author_hash,
    timestamp(created_utc) as created_at,
    timestamp(fetched_at) as fetched_at
  from source
  where body is not null
    and lower(body) not in ('[deleted]', '[removed]')
)

select * from renamed
