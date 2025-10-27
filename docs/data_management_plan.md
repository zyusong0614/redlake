# RedLake Data Management Plan (Updated October 2025)
**Authors:** Siyi Song & Zhengyu Song  
**Institution:** University of Illinois Urbana-Champaign  
**Course:** CS598 – Data Curation  

---

## 1. Overview
RedLake curates Reddit posts and comments from **five public subreddits** into a **FAIR- and GDPR-compliant**, analysis-ready dataset for sentiment research.  
It follows the USGS Data Lifecycle Model — *Plan → Acquire → Process → Analyze → Preserve → Publish* — and uses **Google Cloud Platform (GCP)** components for automation and reproducibility.

At this stage, the pipeline is actively tested and operational for `r/technology`, with extensions to four additional subreddits in progress.

---

## 2. Data Description

### 2.1 Collection Scope
RedLake collects data from:
`r/technology`, `r/gaming`, `r/artificial`, `r/Futurology`, and `r/Computers`.

Each scheduled run fetches:
- **10 rising posts per subreddit**
- **5 comments per post**
- Latest trending discussions only (no historical scraping)
  
This approach ensures lightweight, current, and ethically sourced data.

---

### 2.2 Processed Dataset Fields

| Field | Type | Description |
|--------|------|-------------|
| `post_id` / `comment_id` | STRING | Reddit unique IDs (t3_ or t1_). |
| `author_hash` | STRING | SHA-256 hashed username (anonymized). |
| `title` / `body` | STRING | Cleaned post or comment text. |
| `created_utc` | TIMESTAMP | Normalized UTC timestamp. |
| `score` | INTEGER | Upvote count. |
| `num_comments` | INTEGER | Comment count (posts only). |
| `subreddit` | STRING | Source subreddit. |
| `fetched_at` | TIMESTAMP | Data collection time. |

---

### 2.3 Curated Dataset Additions

| Field | Type | Description |
|--------|------|-------------|
| `sentiment_score` | FLOAT | Estimated sentiment proxy (from upvote polarity). |
| `data_quality_flag` | STRING | dbt test validation result. |
| `curation_version` | STRING | Dataset batch version (e.g., `v1.0_2025-10-27`). |
| `metadata_json` | JSON | DataCite/Schema.org-compliant metadata. |
| `processing_time` | TIMESTAMP | Record creation timestamp. |

---

## 3. Collection & Infrastructure

| Component | Technology | Description |
|------------|-------------|-------------|
| API Client | **PRAW 7.7.1+** | Reddit API wrapper. |
| Function | **Cloud Function: `redditfetcher`** | Fetches, anonymizes, and uploads JSON to GCS. |
| Storage | **Google Cloud Storage** | Raw JSON saved in `/raw_json/`. |
| Processing | **dbt + BigQuery** | Cleans and validates raw data into staging and mart layers. |
| Scheduler | **Cloud Scheduler (daily)** | Triggers ingestion with OIDC token authentication. |

Anonymization via **Microsoft Presidio** occurs inside the Cloud Function before upload.

---

## 4. Ethics and Legal Compliance
- Fully compliant with **Reddit API Terms** and **GDPR**.  
- No usernames, URLs, or other personal identifiers stored.  
- `[removed]` and `[deleted]` content automatically excluded.  
- Only anonymized, non-personal data reaches GCS or BigQuery.  
- License: **CC BY-NC 4.0 (non-commercial academic use).**

---

## 5. Data Quality & Documentation

| Metric | Target | Validation Method |
|---------|---------|------------------|
| Duplicate rate | <1% | dbt DISTINCT selection |
| Missing text | <5% | `IS NOT NULL` filters |
| Timestamp validity | 100% | UTC normalization |
| Schema consistency | 100% | dbt schema.yml enforcement |
| Sentiment field coverage | >90% | dbt validation logs |

Quality reports are logged automatically via **dbt test** and visible in **dbt Docs** hosted at `gs://redlake-dbt-docs`.

Metadata standards: **DataCite 4.5** + **Schema.org Dataset**.

---

## 6. Data Preservation

| Stage | Storage | Retention Policy |
|--------|----------|------------------|
| Raw (anonymized) | `gs://redlake/raw_json/` | Permanent |
| Processed | `gs://redlake/processed/` | Permanent |
| Curated | `BigQuery redlake_dw` | Permanent |
| Published | GitHub + Zenodo (DOI) | Permanent |

All stages contain only anonymized, non-personal data.

---

## 7. Roles

| Member | Responsibilities |
|---------|------------------|
| Zhengyu Song | GCP Infrastructure, API Integration, dbt Automation |
| Siyi Song | GDPR Compliance, Metadata Documentation, Sentiment Analysis |
| Shared | Quality validation, reporting, and publication |

---

## 8. References
- Reddit (2021). *Data API Terms.*  
- EU (2016). *GDPR Regulation.*  
- Faundeen, J. L. et al. (2014). *USGS Data Lifecycle Model.*  
- Wilkinson, M. D. et al. (2016). *FAIR Principles.*  
- Google Cloud (2025). *Cloud Data Security Documentation.*

---

## Summary
RedLake ensures ethical, traceable, and compliant Reddit data curation using lightweight GCP automation.  
Its pipeline—from real-time anonymization to dbt validation—forms a transparent, reproducible foundation for research-ready, FAIR-compliant datasets.
