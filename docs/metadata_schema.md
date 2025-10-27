# Metadata Schema (DataCite + Schema.org)

## 1. Objective
To define standardized metadata fields describing the curated Reddit dataset and ensure interoperability and reusability across research repositories.

---

## 2. Field Mapping

| Concept | DataCite Field | Schema.org Property | RedLake Implementation |
|----------|----------------|--------------------|------------------------|
| Dataset Identifier | `identifier` | `@id` | Auto-generated batch timestamp (e.g., `2025-10-27T15:00Z`) |
| Creator | `creator.name` | `author` | RedLake Team (“Zhengyu Song, Siyi Song”) |
| Title | `title` | `name` | “RedLake Curated Reddit Dataset – r/technology Pilot Batch” |
| Description | `description` | `description` | “Anonymized, FAIR-compliant Reddit posts and comments for sentiment analysis.” |
| Creation Date | `dateCreated` | `dateCreated` | Derived from GCS folder timestamp. |
| License | `rightsURI` | `license` | “https://creativecommons.org/licenses/by-nc/4.0/” |
| Keywords | `subject` | `keywords` | “Reddit, sentiment analysis, data curation, FAIR data” |
| Version | `version` | `version` | Batch increment (`v1`, `v2`, etc.) |
| Distribution URL | `relatedIdentifier` (type: URL) | `distribution` | GCS and BigQuery access links. |

---

## 3. Example YAML Metadata

```yaml
identifier: "redlake_batch_2025-10-27T15:00Z"
creator:
  - name: "Zhengyu Song"
  - name: "Siyi Song"
title: "RedLake Curated Reddit Dataset – r/technology Pilot Batch"
description: "An anonymized, FAIR-compliant Reddit dataset curated via GCP and dbt pipelines."
dateCreated: "2025-10-27"
license: "https://creativecommons.org/licenses/by-nc/4.0/"
subject:
  - "Reddit"
  - "Sentiment Analysis"
  - "Data Curation"
  - "FAIR Data"
version: "v1"
relatedIdentifiers:
  - type: URL
    value: "https://console.cloud.google.com/bigquery?project=redlake-474918&d=redlake_dw"
