# RedLake Data Management Plan (Updated October 2025)
**Authors:** Siyi Song & Zhengyu Song  
**Institution:** University of Illinois Urbana-Champaign  
**Course:** CS598 – Data Curation  

## 1. Overview
RedLake curates Reddit posts and comments from public subreddits into a FAIR-compliant, legally compliant, and analysis-ready dataset for sentiment analysis.  
It follows the USGS Data Lifecycle Model: Plan → Acquire → Process → Analyze → Preserve → Publish using Google Cloud Platform (GCP) tools and ethical data management.

## 2. Data Description
RedLake collects data from five public subreddits:
`r/technology`, `r/gaming`, `r/artificial`, `r/Futurology`, and `r/Computers`.

### 2.1 Processed Dataset Fields
| Field | Type | Description |
|--------|------|-------------|
| id | STRING | Reddit unique ID (t3_ or t1_). |
| author_hash | STRING | SHA-256 hashed username (anonymized). |
| title | STRING | Cleaned post title. |
| body | STRING | Cleaned post/comment text (HTML removed). |
| created_utc | TIMESTAMP | UTC-standardized timestamp. |
| score | INTEGER | Upvotes count. |
| num_comments | INTEGER | Comment count (for posts). |
| subreddit | STRING | Subreddit name. |
| fetched_at | TIMESTAMP | Data collection time. |

### 2.2 Final Curated Dataset Fields
| Field | Type | Description |
|--------|------|-------------|
| All above |  | Retained as base. |
| sentiment_label | STRING | Sentiment (positive, neutral, negative). |
| sentiment_score | FLOAT | Confidence score from NLP model. |
| data_quality_flag | STRING | Validation result (valid, duplicate_removed). |
| curation_version | STRING | Version ID (e.g., v1.0_2025-10-24). |
| metadata_json | JSON | DataCite/Schema.org metadata embedded. |
| processing_time | TIMESTAMP | Record creation time. |

## 3. Collection & Infrastructure
- API Client: PRAW v7.7.1+  
- User-Agent:
  RedLakeBot/0.2 (academic research by u/YOUR_USERNAME, CS598 UIUC)
- Pipeline:
  Reddit API → Cloud Function (fetch) → GCS /raw_json/
              → Cloud Function (process) → GCS /processed/
              → BigQuery redlake_dw → Curated dataset
- Filters: Posts/comments marked [removed] or [deleted] are ignored.  
- Anonymization: SHA-256 hashing of usernames applied before storage.  
- Scheduling: Cloud Scheduler triggers daily runs.

## 4. Ethics and Legal Compliance
- Complies with Reddit API Terms and GDPR.  
- No usernames, IPs, or personal identifiers retained.  
- [removed] or [deleted] content skipped automatically.  
- Raw data is anonymized before storage → classified as non-personal data.  
- License: CC BY-NC 4.0 (non-commercial academic use).  

## 5. Data Quality & Documentation
| Metric | Target | Validation |
|---------|---------|-------------|
| Duplicate rate | <1% | Spark deduplication |
| Missing text | <5% | Filter [removed], [deleted] |
| Timestamp validity | 100% | UTC conversion |
| Sentiment coverage | >90% | NLP API logs |

All validation results stored as data_quality_report.json in /processed/reports/.  
Metadata standards: DataCite + Schema.org JSON-LD.

## 6. Data Preservation
| Stage | Location | Retention |
|--------|-----------|------------|
| Raw (anonymized) | GCS /raw_json/ | Permanent |
| Processed | GCS /processed/ | Permanent |
| Curated | BigQuery redlake_dw | Permanent |
| Published | GitHub + Zenodo (DOI) | Permanent |

## 7. Roles
| Member | Role |
|---------|------|
| Zhengyu Song | GCP infrastructure, Dataproc, Iceberg integration |
| Siyi Song | GDPR compliance, metadata, sentiment analysis |
| Shared | Documentation, testing, publishing |

## 8. References
- Reddit (2021). Data API Terms.  
- European Union (2016). GDPR Regulation.  
- Faundeen, J. L. et al. (2014). USGS Data Lifecycle Model.  
- Wilkinson, M. D. et al. (2016). FAIR Principles.  
- Google Cloud (2025). Cloud Data Security Documentation.  

## Summary
RedLake applies real-time anonymization, ethical filtering, and transparent metadata tracking to ensure that every stage—from data acquisition to publication—is legally compliant and reproducible.
