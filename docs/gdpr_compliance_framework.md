# RedLake Project – GDPR Compliance Framework (Updated October 2025)
**Authors:** Siyi Song & Zhengyu Song  
**Institution:** University of Illinois Urbana-Champaign  
**Course:** CS598 – Data Curation  

---

## 1. Overview
The RedLake project collects **public Reddit content** for academic sentiment analysis under strict **GDPR** and **Reddit API** compliance.  
Although Reddit data is public, RedLake treats all content as potentially identifying and applies **real-time anonymization** to guarantee that no personal data (as defined in GDPR Recital 26) is retained or shared.

At the current stage, only **r/technology** has been fully tested for end-to-end anonymization and ingestion, validating the design for later subreddit expansion.

---

## 2. Data Nature and Legal Basis

| Aspect | Description |
|---------|-------------|
| **Data type** | Reddit posts and comments from public subreddits |
| **Potential identifiers** | Usernames, URLs, and textual self-disclosures |
| **Legal basis** | Legitimate interest for academic research (GDPR Art. 6(1)(f)) |
| **Purpose** | To create anonymized, reusable social media datasets for analysis |
| **Scope** | Five subreddits: r/technology, r/gaming, r/artificial, r/Futurology, r/Computers |

All data processing remains non-commercial and educational.

---

## 3. Anonymization and Data Minimization

| GDPR Principle | RedLake Implementation |
|----------------|------------------------|
| **Remove direct identifiers** | Usernames hashed immediately using SHA-256 + salt. |
| **Remove indirect identifiers** | Links, flairs, and self-mentions redacted using Presidio. |
| **Exclude deleted content** | `[removed]` and `[deleted]` posts/comments ignored. |
| **Data minimization** | Only essential fields retained (id, author_hash, title, body, score, subreddit, timestamps). |
| **Aggregation and pseudonymization** | Only aggregated or hashed data is ever stored or shared. |

---

## 4. Data Retention and Deletion Policy

**Clarification:**  
Raw Reddit data is already anonymized at collection, therefore no personal data exists in storage.

| Stage | Location | Retention | Notes |
|--------|-----------|------------|-------|
| Raw (anonymized) | `gs://redlake/raw_json/` | Permanent | SHA-256 hashed usernames, no PII |
| Processed | `gs://redlake/processed/` | Permanent | Cleaned via dbt models |
| Curated | `BigQuery redlake_dw` | Permanent | Used for analysis |
| Deleted/flagged data | Excluded | N/A | [removed]/[deleted] skipped |

---

## 5. Rights of Data Subjects

Although anonymized data no longer identifies individuals, RedLake maintains ethical transparency:

| GDPR Right | Implementation |
|-------------|----------------|
| **Access** | Public metadata and docs available on GitHub |
| **Rectification** | Not applicable – immutable Reddit content |
| **Erasure (“Right to be Forgotten”)** | Fulfilled by excluding deleted content from ingestion |
| **Portability** | Data provided in interoperable formats (CSV, Parquet, BigQuery views) |

---

## 6. Security and Access Control

- **GCP IAM roles** restrict dataset access to project members.  
- **Google Secret Manager** secures API keys and salts.  
- **Cloud Logging** tracks all anonymization and ingestion events.  
- **Encryption** at rest and in transit via GCP-managed keys.

All compliance logs are versioned and auditable.

---

## 7. Ethical and Institutional Review

- RedLake adheres to **r/reddit4researchers** guidelines and **UIUC Research Data Policy**.  
- As the dataset contains no identifiable information, **IRB review is not required**.  
- Transparency is maintained through public documentation (GitHub + Zenodo).

---

## 8. References
- European Union (2016). *General Data Protection Regulation (GDPR).*  
- Reddit (2021). *Data API Terms.*  
- Wilkinson, M. D. et al. (2016). *FAIR Guiding Principles.* *Scientific Data*, 3(1), 160018.  
- University of Illinois. (2024). *Research Data Policy.*  

---

## Summary
RedLake transforms Reddit data into anonymized, non-personal information through **real-time Presidio anonymization**, **SHA-256 hashing**, and **ethical filtering**.  
Since no PII is ever stored or accessible, the project fully satisfies GDPR’s data minimization, purpose limitation, and integrity principles — ensuring safe, legal, and transparent long-term data stewardship.
