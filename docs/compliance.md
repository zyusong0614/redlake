# Compliance Overview (GDPR + FAIR Alignment)

## 1. Purpose
This document describes how the RedLake project ensures compliance with the **EU GDPR (Article 5)** and the **FAIR Guiding Principles** for scientific data management.

---

## 2. GDPR Compliance Summary

| GDPR Principle | Implementation in RedLake |
|----------------|---------------------------|
| **Lawfulness & Transparency** | Data is collected from public Reddit APIs for academic research; no private messages or user profiles are accessed. |
| **Purpose Limitation** | Only posts and comments containing predefined research keywords (e.g., *startup*, *idea*, *problem*) are collected. |
| **Data Minimization (Art. 5)** | Personal data fields (email, phone, names, usernames) are detected and redacted via Microsoft Presidio before storage. |
| **Accuracy** | Data cleaning ensures removal of duplicates and null fields before analysis. |
| **Storage Limitation** | Raw PII is never stored; only hashed `author_id` is retained for analysis integrity. |
| **Integrity & Confidentiality** | GCP IAM permissions restrict access to project service accounts only. |
| **Accountability** | All ETL and dbt runs are logged via Cloud Logging and Cloud Build for audit trail. |

---

## 3. FAIR Principles Mapping

| FAIR Principle | Implementation |
|----------------|----------------|
| **Findable** | dbt Docs and metadata schema (DataCite/Schema.org) hosted on GCS `redlake-dbt-docs`. |
| **Accessible** | BigQuery dataset `redlake_dw` with read permissions for instructors and collaborators. |
| **Interoperable** | Standardized SQL and YAML schema definitions usable across data platforms. |
| **Reusable** | Complete documentation, metadata, and anonymization procedures enable safe reuse of the curated dataset. |

---

## 4. References
- GDPR (EU 2016/679) Articles 5 and 25  
- Wilkinson et al. (2016). FAIR Guiding Principles for Scientific Data Management  
- Reddit Data API Terms (2021)
