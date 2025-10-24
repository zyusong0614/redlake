# RedLake Project – GDPR Compliance Framework (Updated October 2025)
**Project Title:** RedLake – A Legally Compliant, Analysis-Ready Dataset of Reddit Posts and Comments for Sentiment Analysis  
**Authors:** Siyi Song & Zhengyu Song  
**Institution:** University of Illinois Urbana-Champaign  
**Date:** October 2025  

## 1. Overview
The RedLake project processes publicly available Reddit content for academic research. Although Reddit data is public, RedLake adopts strict data protection and ethical handling measures to comply with the General Data Protection Regulation (GDPR) and Reddit’s API Terms of Service.  
All personal identifiers (e.g., usernames) are irreversibly anonymized at the time of collection, ensuring the dataset no longer qualifies as “personal data” under GDPR Recital 26.

## 2. Data Nature and Legal Basis
| Aspect | Description |
|-------------|----------------|
| Data type | Reddit posts and comments from public subreddits |
| Personal data potentially included | Usernames, timestamps, and text that may contain self-reference |
| Legal basis | Legitimate interest for academic research (GDPR Article 6(1)(f)) |
| Purpose | To produce an anonymized dataset for sentiment analysis and social computing research |
| Scope | Five public subreddits: r/technology, r/gaming, r/artificial, r/Futurology, r/Computers |

## 3. Anonymization and Data Minimization
| Principle | Implementation in RedLake |
|----------------|-------------------------------|
| Remove direct identifiers | Reddit usernames are hashed immediately upon collection using SHA-256; no original usernames are ever stored. |
| Remove indirect identifiers | Exclude user flair, URLs, location mentions, or external links. |
| Filter deleted content | Records with [removed] or [deleted] are ignored during ingestion. |
| Data minimization | Only necessary fields are retained (id, author_hash, title, body, created_utc, score, num_comments, subreddit, fetched_at). |
| Aggregation | Only anonymized and aggregated results are shared publicly. |

## 4. Data Retention and Deletion
**Clarification on “Raw Data”:**  
Raw Reddit data is anonymized at collection — usernames are hashed and [removed]/[deleted] content is skipped.  
Therefore, “raw data” in this project does not contain personal data and is classified as anonymized non-personal data under GDPR Recital 26.

| Stage | Storage | Retention Period | Notes |
|------------|-------------|----------------------|-----------|
| Raw (already anonymized) | gs://redlake/raw_json/ | Permanent | Contains no personal identifiers |
| Processed | gs://redlake/processed/ | Permanent | Cleaned and validated |
| Curated | BigQuery redlake_dw.reddit_posts_curated | Permanent | For analysis and publication |
| Deleted content | Ignored | N/A | [removed] and [deleted] skipped entirely |

## 5. Rights of Data Subjects
Although the dataset is anonymized and does not identify individuals, RedLake upholds transparency and ethical responsibility by publishing compliance documentation and metadata.

| GDPR Principle | Implementation |
|--------------------|--------------------|
| Right to access | Public metadata available on GitHub |
| Right to rectification | Not applicable — public immutable Reddit content |
| Right to erasure | Deleted Reddit posts are excluded automatically |
| Data portability | Curated data available in interoperable formats (CSV, Parquet, BigQuery) |

## 6. Security and Access Control
- GCP IAM roles restrict access to project contributors only.  
- All data encrypted at rest and in transit.  
- API credentials stored securely in Google Secret Manager.  
- All processing jobs logged via Cloud Logging for auditability.  

## 7. Ethical Review
RedLake aligns with Reddit’s r/reddit4researchers guidelines and the University of Illinois Research Data Policy.  
Since all collected data are public and anonymized, the project does not require IRB review.

## 8. References
- European Union. (2016). General Data Protection Regulation (GDPR).  
- Reddit. (2021). Data API Terms. https://redditinc.com/policies/data-api-terms  
- Wilkinson, M. D., et al. (2016). The FAIR Guiding Principles. Scientific Data, 3, Article 160018.  

## Summary
RedLake’s collection process transforms Reddit data into fully anonymized, non-personal information through real-time SHA-256 hashing and deletion filtering.  
As no identifiable information is stored or shared, long-term retention of raw and processed datasets remains fully GDPR-compliant.
