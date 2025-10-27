# Analysis Plan and Next Step Expansion

## 1. Objective
This document defines the analytical component of the **RedLake** project.  
It outlines current analytical models implemented via **dbt + BigQuery**, explains the rationale behind their design, and presents a roadmap for expanding toward full-fledged NLP-based sentiment analysis.  

The primary goal of the analytical phase is to transform cleaned Reddit data into interpretable, FAIR-compliant metrics that enable future research on community sentiment and topic trends.

---

## 2. Current Analytical Implementation

The analytical layer consists of **two dbt marts**:

1. `reddit_sentiment_analysis.sql` — baseline sentiment proxy  
2. `reddit_data_quality_summary.sql` — dataset-level quality and volume summary  

These marts provide lightweight, reproducible insights directly in **BigQuery**, following FAIR R1.2 reproducibility principles.

### a. `reddit_sentiment_analysis.sql`
This model estimates sentiment using post engagement metrics (score polarity) as a heuristic proxy:

```sql
SELECT
  post_id,
  title,
  post_score,
  avg_comment_score,
  subreddit,
  created_at,
  CASE WHEN post_score >= 0 THEN 0.5 ELSE -0.5 END AS sentiment_score
FROM {{ ref('int_posts_comments_joined') }}
