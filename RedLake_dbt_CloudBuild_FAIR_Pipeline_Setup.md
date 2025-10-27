# 🧱 RedLake dbt + Cloud Build FAIR Pipeline Setup

**Project:** RedLake – Reddit Data Curation & FAIR Pipeline  
**Authors:** Siyi Song & Zhengyu Song  
**Institution:** University of Illinois Urbana-Champaign  
**Course:** CS598 – Data Curation  
**Last Updated:** October 2025  

---

## 🧠 Overview

This document provides the **technical setup and deployment guide** for RedLake’s dbt-based data pipeline and continuous integration on **Google Cloud Build (GCB)**.  
It ensures the dataset is transformed, validated, and documented under **FAIR and GDPR** principles.

### Pipeline Scope

| Layer | Description | Tools |
|-------|--------------|-------|
| **Acquire** | Reddit data collection via PRAW API + Presidio anonymization | Cloud Function + Cloud Scheduler |
| **Process** | JSON ingestion → staging tables | BigQuery external table |
| **Transform & Validate** | Cleaning, deduplication, sentiment prep | dbt + dbt-expectations |
| **Publish** | Docs and curated views | Cloud Build + GCS Hosting |

---

## 🏗️ System Architecture

```
[Reddit API] → [Cloud Function (redditfetcher)]
       │
       ├── Anonymize (Presidio)
       ├── Upload JSON → GCS (gs://redlake/raw_json/)
       │
       ▼
[BigQuery] ← dbt run via Cloud Build
       ├── Stage: stg_reddit_posts.sql / stg_reddit_comments.sql
       ├── Intermediate: reddit_sentiment_analysis.sql
       ├── Metrics: reddit_data_quality_summary.sql
       └── Docs: dbt docs generate → GCS (FAIR HTML docs)
```

---

## ⚙️ Environment Requirements

| Component | Version | Purpose |
|------------|----------|----------|
| Python | 3.11+ | Cloud Function runtime |
| dbt | 1.11.0+ | Data transformation & docs |
| dbt-bigquery | 1.10.2+ | BigQuery adapter |
| dbt-expectations | latest | Data quality testing |
| Google Cloud SDK | 450.0+ | Deployment CLI |
| GCS Bucket | `redlake` | Raw and processed data storage |
| BigQuery Dataset | `redlake_dw` | Analytical data warehouse |

---

## 🪄 Step 1: dbt Project Setup

```bash
cd dbt
dbt init dbt_redlake
```

Update `dbt_project.yml`:
```yaml
name: 'dbt_redlake'
version: '1.0.0'
profile: 'redlake_profile'
config-version: 2
```

Then configure your **profiles.yml** (usually at `~/.dbt/profiles.yml`):

```yaml
redlake_profile:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: redlake-474918
      dataset: redlake_dw
      threads: 4
      keyfile: /workspace/cert/redlake-service-account.json
      timeout_seconds: 300
```

---

## 🧹 Step 2: dbt Model Structure

| Folder | File | Purpose |
|---------|------|----------|
| `models/staging/` | `stg_reddit_posts.sql` | Clean and standardize post data |
|  | `stg_reddit_comments.sql` | Clean comment data |
| `models/intermediate/` | `reddit_sentiment_analysis.sql` | Join posts & comments with metrics |
| `models/marts/` | `reddit_data_quality_summary.sql` | Aggregated data quality summary |
| `models/schema.yml` | Schema tests + descriptions |
| `macros/` | Quality checks (e.g., missing timestamps) |

---

## 🧪 Step 3: dbt Testing and Documentation

### Run Core Pipeline
```bash
dbt deps
dbt run
```

### Run Quality Tests
```bash
dbt test
```

### Generate FAIR Documentation
```bash
dbt docs generate
```

This creates a browsable documentation site under `target/` with lineage graphs, model metadata, and test results.

---

## ☁️ Step 4: Cloud Build Continuous Deployment

### File: `cloudbuild.yaml`

```yaml
substitutions:
  _DBT_DOCS_BUCKET: redlake-dbt-docs

steps:
  - name: gcr.io/cloud-builders/gcloud
    id: "Install system dependencies & dbt"
    entrypoint: bash
    args:
      - -c
      - |
        echo "🧰 Installing dbt & dependencies"
        apt-get update && apt-get install -y python3-pip git
        pip3 install --upgrade pip
        pip3 install dbt-bigquery dbt-expectations

  - name: gcr.io/cloud-builders/gcloud
    id: "Run dbt"
    entrypoint: bash
    args:
      - -c
      - |
        echo "▶️ Running dbt models..."
        dbt deps
        dbt run
        dbt test
        dbt docs generate

  - name: gcr.io/cloud-builders/gsutil
    id: "Upload docs"
    args:
      - -m
      - rsync
      - -r
      - target/
      - gs://${_DBT_DOCS_BUCKET}/

timeout: 1800s
options:
  logging: CLOUD_LOGGING_ONLY
```

---

## 🚀 Step 5: Triggering Builds

### Option A – Manual Build
```bash
gcloud builds submit --config cloudbuild.yaml .
```

### Option B – Trigger on Push to `main`
In **Cloud Build Console**:
- Create a trigger → Connect to GitHub repo
- Branch filter: `main`
- Build config: `cloudbuild.yaml`

Now every commit to `main`:
- Runs all dbt models  
- Executes validation tests  
- Publishes updated FAIR documentation to  
  ➜ **https://storage.googleapis.com/redlake-dbt-docs/index.html**

---

## 🧩 Step 6: FAIR Metadata Integration

Each dbt model embeds **DataCite + Schema.org** fields in its `schema.yml`, for example:

```yaml
models:
  - name: stg_reddit_posts
    description: "Anonymized Reddit posts (GDPR-compliant)"
    columns:
      - name: post_id
        description: "Unique Reddit post identifier (t3_)"
      - name: author_hash
        description: "SHA-256 hashed author username"
    meta:
      datacite:
        resourceType: "Dataset"
        creators:
          - name: "Siyi Song"
        publisher: "University of Illinois Urbana-Champaign"
        license: "CC BY-NC 4.0"
```

FAIR Documentation generated by `dbt docs generate` includes these metadata fields in the lineage graph and model pages.

---

## 🧮 Step 7: Validation Metrics

| Metric | Target | Validation | FAIR Mapping |
|---------|---------|-------------|----------------|
| Duplicate rate | < 1% | dbt-expectations `expect_column_values_to_be_unique` | R1.2 |
| Missing text | < 5% | `expect_column_values_to_not_be_null` | R1.2 |
| Timestamp validity | 100% | custom macro test | R1.2 |
| Sentiment coverage | > 90% | NLP API completeness check | R1.2 |

---

## 🛡️ Step 8: GDPR and Compliance Safeguards

| Principle | Implementation |
|------------|----------------|
| **Data Minimization** | Collects only post ID, text, score, timestamps, subreddit |
| **Anonymization** | SHA-256 hashed usernames via Presidio |
| **Right to Erasure** | [removed]/[deleted] skipped automatically |
| **Access Control** | GCP IAM roles restrict access |
| **Transparency** | Documentation published on GitHub + GCS |

All compliance documentation stored in `/docs/`:
- `gdpr_compliance_framework.md`
- `compliance.md`
- `data_management_plan.md`

---

## 🧰 Troubleshooting

| Issue | Cause | Solution |
|--------|--------|----------|
| `MissingArgumentsPropertyInGenericTestDeprecation` | dbt v1.11 deprecation warning | Update to `dbt-expectations` ≥ 0.9 |
| `Memory limit exceeded` | Cloud Run 512 MiB limit | Increase via `gcloud run services update redditfetcher --memory 1Gi` |
| `manifest.json not found` | First-time dbt run | Ignore – resolves on subsequent builds |
| `gsutil rsync permission denied` | GCS bucket ACL issue | Ensure service account has `Storage Object Admin` |

---

## 🧾 Deployment Validation Checklist

✅ Cloud Function deployed successfully  
✅ GCS receives anonymized JSON batches  
✅ BigQuery dataset `redlake_dw` populated  
✅ dbt models run without failure  
✅ FAIR documentation hosted publicly  
✅ GDPR compliance metadata available  

---

## 📚 References

- [Reddit API Documentation](https://www.reddit.com/dev/api)  
- [dbt-bigquery Docs](https://docs.getdbt.com/reference/warehouse-profiles/bigquery-profile)  
- [FAIR Principles – Wilkinson et al. (2016)](https://www.nature.com/articles/sdata201618)  
- [Google Cloud Build Documentation](https://cloud.google.com/build/docs)  
- [Microsoft Presidio GitHub](https://github.com/microsoft/presidio)

---

## ✅ Summary

The **RedLake FAIR Pipeline** is an end-to-end reproducible data curation system.  
Using **dbt + Cloud Build**, it automates transformation, validation, and FAIR documentation generation while maintaining **GDPR compliance**.  

It serves as a scalable reference for ethically responsible, cloud-native social data research.

```
© 2025 RedLake Project – University of Illinois Urbana-Champaign
```
