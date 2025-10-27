# Data Quality Metrics (FAIR R1.2 Compliance)

## 1. Objective
This document defines the data quality metrics and validation logic used in the RedLake project to ensure that curated Reddit data adheres to the **FAIR Principle R1.2: “(Meta)data are associated with detailed provenance”** and meet reproducible data quality standards.

---

## 2. Implementation Overview
Data quality checks are implemented using **dbt (Data Build Tool)** combined with the **`dbt-expectations`** package.  
Each model undergoes automated validation when `dbt run` or `dbt test` is executed in the Cloud Build pipeline.  
Test results are logged in the dbt artifacts (`manifest.json`, `run_results.json`) and surfaced through dbt Docs hosted in GCS.

---

## 3. Quality Dimensions and Corresponding Tests

| Quality Dimension | Validation Logic | dbt Test / Expectation | Target Columns | FAIR Mapping |
|--------------------|------------------|------------------------|----------------|---------------|
| **Uniqueness** | Ensure each record (post/comment) is unique | `unique` test | `post_id`, `comment_id` | F1 (Findable) |
| **Completeness** | No missing identifiers or text content | `not_null` test | `title`, `body`, `author_hash` | R1.2 (Reusable) |
| **Validity / Range** | Scores must fall within logical bounds | `expect_column_values_to_be_between` | `score`, `num_comments` | R1.2 (Data Quality) |
| **Integrity** | Foreign key consistency between posts/comments | `referential_integrity` test | `parent_id → post_id` | I1 (Interoperable) |
| **Timeliness** | Timestamp must be valid UTC format | Custom SQL test (`IS TIMESTAMP`) | `created_at`, `fetched_at` | A1 (Accessible) |

---

## 4. Example dbt Test Configuration

```yaml
version: 2
models:
  - name: stg_reddit_posts
    description: "Cleaned and standardized Reddit posts"
    columns:
      - name: post_id
        tests: [unique, not_null]
      - name: score
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              max_value: 100000
  - name: stg_reddit_comments
    description: "Cleaned and standardized Reddit comments"
    columns:
      - name: comment_id
        tests: [unique, not_null]
      - name: score
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: -10
              max_value: 10000
