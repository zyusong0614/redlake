# Anonymization Procedures

## 1. Objective
This document details how the RedLake data pipeline anonymizes Reddit data to ensure compliance with **GDPR Article 5** (Data Minimization) and Reddit API Terms of Use.  
The goal is to guarantee that **no personally identifiable information (PII)** is stored in Google Cloud Storage (GCS) or BigQuery.

---

## 2. Framework Used
The anonymization process is implemented using **Microsoft Presidio**, integrated into the `redditfetcher` Cloud Function.  
Presidio performs two main tasks:

1. **Detection (Analyzer Engine)** — Identifies PII entities within text using built-in NLP recognizers.  
2. **Redaction (Anonymizer Engine)** — Replaces sensitive entities with placeholders or pseudonyms.

Both steps occur **before any data is written to GCS**, ensuring that downstream systems (BigQuery, dbt) handle only sanitized data.

---

## 3. PII Detection and Replacement Rules

| Entity Type | Example | Anonymization Action | Field(s) Affected |
|--------------|----------|----------------------|-------------------|
| `PERSON` | “John Doe” | Replace with `[REDACTED_PERSON]` | Post or comment text |
| `EMAIL_ADDRESS` | “john@example.com” | Replace with `[REDACTED_EMAIL]` | Post or comment text |
| `PHONE_NUMBER` | “+1-650-555-1234” | Replace with `[REDACTED_PHONE]` | Post or comment text |
| `LOCATION` | “San Francisco” | Replace with `[REDACTED_LOCATION]` | Post or comment text |
| `URL` | “https://linkedin.com/…” | Replace with `[REDACTED_URL]` | Post or comment text |
| `USERNAME` | “u/someuser” | Hash using SHA-256 + salt → `author_hash` | Author field |

---

## 4. Hashing Implementation

Usernames are pseudonymized instead of deleted to preserve analytical relationships (e.g., average comment count per user).  
Hashing ensures **non-reversible, consistent identifiers** within each batch.

```python
import hashlib, os
salt = os.environ.get("HASH_SALT")
author_hash = hashlib.sha256((username + salt).encode("utf-8")).hexdigest()
