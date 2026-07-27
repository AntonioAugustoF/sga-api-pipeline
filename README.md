# Data Engineering Project - SGA API Pipeline

[![CI](https://github.com/AntonioAugustof/sga-api-pipeline/actions/workflows/tests.yml/badge.svg)](https://github.com/AntonioAugustof/sga-api-pipeline/actions/workflows/tests.yml)
![License](https://img.shields.io/badge/License-MIT-green)

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-data-150458?logo=pandas&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white)
![Prefect](https://img.shields.io/badge/Prefect-orchestration-024DFD?logo=prefect&logoColor=white)
![Power BI](https://img.shields.io/badge/Power_BI-dashboards-F2C811?logo=powerbi&logoColor=black)

This repository contains the implementation of a data pipeline (SGA API Pipeline) designed to extract, transform, and load data efficiently, ensuring data consistency and reliability for downstream analysis and reporting.

The pipeline architecture is built using modular Python scripts and industry-standard practices for clean, scalable data engineering.

Access structured and cleaned data ready for consumption. 💪

---

## Architecture Overview

```mermaid
flowchart LR
    API["SGA API<br/>(external)"]

    subgraph Extract["Extract"]
        EX["Paginated fetch<br/>retry + backoff"]
    end

    subgraph Transform["Transform (Pandas)"]
        TR["Clean, type-cast,<br/>business rules,<br/>value allocation"]
    end

    subgraph Load["Load"]
        LD["Upsert / SCD2 /<br/>snapshot<br/>+ point-in-time SK"]
    end

    DW[("PostgreSQL<br/>Data Warehouse<br/>star schema")]
    BI["Power BI<br/>dashboards"]

    API --> EX --> TR --> LD --> DW --> BI

    RAW[/"data/raw<br/>JSON"/]
    PROC[/"data/processed<br/>Parquet"/]
    EX -.-> RAW -.-> TR
    TR -.-> PROC -.-> LD

    subgraph Ops["Orchestration & Observability"]
        PF["Prefect flow<br/>daily cron 03:00"]
        AL["Discord alert<br/>on failure"]
        CI["GitHub Actions<br/>pytest on push"]
    end

    PF -. orchestrates .-> Extract
    PF -. orchestrates .-> Transform
    PF -. orchestrates .-> Load
    PF -. on failure .-> AL
```

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Architecture & Folder Structure](#architecture--folder-structure)
- [How It Works](#how-it-works)
  - [Data Extraction](#data-extraction)
  - [Data Transformation](#data-transformation)
  - [Data Load](#data-load)
  - [Data Model & Analytical Views](#data-model--analytical-views)
  - [Infrastructure & Orchestration](#infrastructure--orchestration)
- [Entities](#entities)
- [Testing & CI](#testing--ci)
- [Prerequisites](#prerequisites)
- [Running Project](#running-project)
- [Running with Docker](#running-with-docker)
- [Scheduling](#scheduling)
- [License](#license)
- [Contact](#contact)

---

## Architecture & Folder Structure

The project follows a rigorous separation of concerns to ensure maintainability:

```
sga-api-pipeline/
├── .github/workflows/  # Continuous integration (pytest on push/PR)
├── data/
│   ├── raw/            # Raw JSON files extracted from the API
│   └── processed/      # Cleaned Parquet files ready for loading
├── extract/            # Extraction scripts (API connectors)
├── infra/              # Connections, config, logging, retry, alerts
├── load/               # Loading modules (PostgreSQL insertions)
├── logs/               # Application and pipeline execution logs
├── orchestrators/      # Prefect flow and scheduling scripts
├── sql/                # Hand-written analytical views
├── tests/              # Unit tests (pytest)
├── transform/          # Data cleaning, processing, and business logic (Pandas)
├── Dockerfile          # Pipeline application image
└── docker-compose.yml  # Full stack: pipeline + PostgreSQL
```

---

## How It Works

### Data Extraction

The modules inside the `/extract` folder are responsible for connecting to the SGA API. They fetch data in paginated batches across all available statuses, ensuring connection security through environment variables (`.env`). Raw data is saved as JSON files in `data/raw/`.

Invoices use a multi-window incremental strategy (by emission, payment, and due date) to capture new and recently changed records. Delinquency uses a full-history extract — querying only `status=2` (open) with no date filter — to ensure no overdue invoice is missed regardless of when it was issued.

Transient server errors (HTTP 5xx, timeouts, dropped connections) are retried with exponential backoff via the shared `infra/retry.py` decorator; genuine client errors (4xx) fail fast without retrying.

### Data Transformation

Inside the `/transform` folder, data undergoes rigorous cleaning and structuring:

- Data type casting and formatting.
- Handling missing values and duplicates.
- Serialization of nested fields (arrays and dictionaries) into flat, relational columns.
- Business rules (aging, payment reconciliation, age) for invoices, delinquency and customers.
- Value allocation: an invoice covering multiple vehicles is exploded into one row per vehicle, splitting `valor_boleto` evenly so `SUM(valor_rateado)` always reconstructs the original invoice value. This feeds the invoice-vehicle bridge.

Cleaned data is saved as Parquet files in `data/processed/`.

### Data Load

The `/load` folder safely writes processed data into PostgreSQL using the following strategies:

| Strategy | Tables | Behavior |
|---|---|---|
| Upsert | `dim_cooperatives`, `dim_regionals`, `dim_volunteers`, `dim_status`, `dim_status_invoice`, `fact_invoices`, `bridge_invoices_vehicles` | Inserts new records; updates existing ones by natural (or composite) key |
| SCD Type 2 | `dim_customers`, `dim_vehicles` | Tracks attribute history in place via `vigente`/`valido_de`/`valido_ate`: changes to monitored columns close the current version and open a new one; other attribute changes are refreshed without versioning. Natural keys present in the source but with no current version get one opened, so a rerun heals rows left unversioned by earlier runs |
| Daily snapshot replace | `fact_delinquency_snapshot` | Deletes and reinserts that day's slice of open invoices; re-runs on the same day are idempotent |

Cross-cutting load guarantees:

- **Schema reconciliation:** before every upsert or SCD2 load, the destination table's schema is reconciled against the incoming DataFrame — missing columns are added automatically (`ALTER TABLE ... ADD COLUMN`), so new business-rule columns introduced upstream never fail with `UndefinedColumn`.
- **Explicit typing:** each temp table is created with an explicit SQLAlchemy type map, so a column never silently lands as the wrong type (e.g. a date arriving as `TEXT`, or a nullable surrogate key drifting to `DOUBLE PRECISION`).
- **Partial-extraction guard:** if an incoming dimension's row count drops more than 30% versus what is already loaded, the load is refused for that entity instead of silently shrinking the dimension.
- **Status coverage guard:** the source only returns the statuses currently enabled for the API user, and a status that stops being returned is indistinguishable from one that never existed — entities in it are silently never extracted. Every load diffs the incoming status codes against the ones already in the DW and alerts on codes **added or removed**, without failing the load.
- **Audit metadata:** rows are stamped with `criado_em`, `atualizado_em` and (where applicable) `data_referencia`. `criado_em` is immutable — excluded from the `ON CONFLICT` update — so reruns never overwrite a row's original creation timestamp.
- **Composite & immutable keys:** `upsert_to_postgres` accepts a composite primary key (e.g. the bridge's `codigo_boleto` + `codigo_veiculo`) and a list of immutable columns to freeze on conflict.

### Data Model & Analytical Views

```mermaid
erDiagram
    dim_customers ||--o{ fact_invoices : "sk_customer"
    dim_customers ||--o{ fact_delinquency_snapshot : "sk_customer"
    dim_regionals ||--o{ fact_invoices : "codigo_regional"
    dim_cooperatives ||--o{ dim_customers : "codigo_cooperativa"
    dim_volunteers ||--o{ dim_customers : "codigo_voluntario"
    dim_regionals ||--o{ dim_customers : "codigo_regional"
    fact_invoices ||--o{ bridge_invoices_vehicles : "codigo_boleto"
    dim_vehicles ||--o{ bridge_invoices_vehicles : "codigo_veiculo (natural key)"
    dim_status ||--o{ dim_customers : "codigo_situacao"
    dim_status ||--o{ dim_vehicles : "codigo_situacao"
    dim_status_invoice ||--o{ fact_invoices : "codigo_situacao_boleto"

    dim_customers {
        int sk_customer PK
        string codigo_associado "natural key (SCD2)"
        date valido_de
        date valido_ate
        bool vigente
    }
    dim_vehicles {
        int sk_vehicle PK
        string codigo_veiculo "natural key (SCD2)"
        date valido_de
        date valido_ate
        bool vigente
    }
    dim_status {
        string codigo_situacao PK
        string descricao_situacao
        bool situacao_ativa
    }
    dim_status_invoice {
        string codigo_situacao_boleto PK
        string descricao_situacao_boleto
        bool considerado_inadimplencia
        bool pago
    }
    dim_cooperatives {
        string codigo_cooperativa PK
    }
    dim_regionals {
        string codigo_regional PK
    }
    dim_volunteers {
        string codigo_voluntario PK
    }
    fact_invoices {
        string codigo_boleto PK
        int sk_customer FK "point-in-time"
        string codigo_regional FK
        numeric valor_boleto
    }
    fact_delinquency_snapshot {
        string codigo_boleto PK
        date dt_referencia PK
        int sk_customer FK
    }
    bridge_invoices_vehicles {
        string codigo_boleto PK
        string codigo_veiculo PK
        numeric valor_rateado
    }
```

The model is a star schema with surrogate keys on the SCD2 dimensions:

- **Surrogate keys:** `dim_customers` and `dim_vehicles` are SCD2 and carry a serial surrogate key (`sk_customer`, `sk_vehicle`). A natural key repeats across historical versions, so only the surrogate key identifies a *specific* version.
- **Point-in-time attribution:** `fact_invoices` and `fact_delinquency_snapshot` resolve `sk_customer` against the `dim_customers` version effective on the fact's own date, not the current version — so historical analysis reflects who the customer *was* at the time.
- **Invoice-vehicle bridge:** `bridge_invoices_vehicles` resolves the many-to-many between invoices and vehicles (an invoice can bill several vehicles), carrying `qtd_veiculos_boleto` and the pro-rated `valor_rateado`. It relates to `dim_vehicles` by the **natural key**, not by `sk_vehicle` — see *Known limitations* below.
- **Reference dimensions:** `dim_status` and `dim_status_invoice` mirror the source's status lists. They are SCD1 and keyed by the natural code — small, stable reference data where a surrogate key would add a join without buying anything. `dim_status_invoice` also records `considerado_inadimplencia` and `pago`, business rules that otherwise live only in the source API.
- **Foreign keys & indexes:** FK constraints link `fact_invoices` and `fact_delinquency_snapshot` to `dim_customers` (via `sk_customer`) and to `dim_regionals`, and link the SCD2 dimensions to `dim_volunteers`, `dim_regionals` and `dim_cooperatives`. Fact join columns (`sk_customer`, `codigo_associado`, `codigo_regional`) are indexed for BI query performance.

Hand-written views in `sql/views/` support delinquency-by-vehicle analysis:

| View | Attribution | Use case |
|---|---|---|
| `vw_delinquency_by_vehicle_atual` | Vehicle's **current** owner (`dim_vehicles_current`) | "Who do I contact today about this delinquency?" — operational |
| `vw_delinquency_by_vehicle_historico` | Vehicle's owner **on the snapshot date** (SCD2 point-in-time) | Historical performance by volunteer, preserving attribution even if the vehicle later changed hands |

`vw_delinquency_by_vehicle_historico` resolves the vehicle version with a half-open interval
(`dt_referencia >= valido_de AND (valido_ate IS NULL OR dt_referencia < valido_ate)`), so exactly one
version matches even on the day a version is closed and the next one opens.

#### Known limitations

Documented rather than glossed over, since they shape how the model should be queried:

- **The bridge relates to `dim_vehicles` by natural key, not by `sk_vehicle`.** `codigo_veiculo` repeats
  across SCD2 versions, so joining the bridge straight to `dim_vehicles` fans out and double-counts
  `valor_rateado`. Consumers must join through `dim_vehicles_current` (one row per vehicle) — which is
  what the BI model does. The proper fix is to carry `sk_vehicle` on the bridge, resolved point-in-time.
- **Revenue is attributed to the vehicle's *current* volunteer**, a consequence of the item above.
  That is fine for portfolio management, but not for commission: moving a vehicle between volunteers
  rewrites past rankings. Delinquency is unaffected — it has the historical view above.
- **No "unknown member" rows.** Natural keys deleted upstream but still referenced by facts simply fail
  to match, and the affected rows drop out of dimension-sliced analysis instead of landing in an
  explicit bucket.
- **`bridge_invoices_vehicles` has no FK to `dim_vehicles` and no index on `codigo_veiculo`.** A FK here
  would surface missing vehicles as a load error rather than as silently unattributed revenue.

### Infrastructure & Orchestration

**Infrastructure (`/infra`):** Manages the database connection pool (a single cached engine with `pool_pre_ping`), API authentication, environment configuration, structured logging (one log file per day), a reusable retry decorator, and failure alerting.

**Orchestration (`/orchestrators`):** The full ETL flow (Extract → Transform → Load) is a Prefect flow (`run_pipeline`). On failure, an `on_failure` hook posts a formatted message to a Discord webhook — timestamps converted to America/Sao_Paulo, maintainer mentioned to trigger a mobile push — so unattended runs never fail silently.

---

## Entities

| Entity | Table | Notes |
|---|---|---|
| Volunteers | `dim_volunteers` | Upsert by natural key |
| Cooperatives | `dim_cooperatives` | Upsert by natural key |
| Regionals | `dim_regionals` | Upsert by natural key |
| Customers | `dim_customers` | SCD Type 2; surrogate key `sk_customer` |
| Vehicles | `dim_vehicles` | SCD Type 2; surrogate key `sk_vehicle` (currently consumed only by `vw_delinquency_by_vehicle_historico`) |
| Statuses | `dim_status` | Reference dimension (SCD1) for customer/vehicle statuses |
| Invoice statuses | `dim_status_invoice` | Reference dimension (SCD1); carries `considerado_inadimplencia` and `pago` |
| Invoices | `fact_invoices` | Incremental upsert; point-in-time `sk_customer`; multi-window extraction |
| Invoice–Vehicle | `bridge_invoices_vehicles` | Bridge resolving the invoice↔vehicle many-to-many, with pro-rated value |
| Delinquency | `fact_delinquency_snapshot` | Daily snapshot of all open invoices (`status=2`) |

---

## Testing & CI

Unit tests live in `/tests` and run with `pytest`. They cover the transformation helpers, business rules, the retry decorator, the API fetcher, the dimension-drop guard, the status coverage guard, and the SCD2 behavior — including a regression test ensuring a closed version always has its replacement opened — all mocked, with no dependency on a live API or database.

A GitHub Actions workflow (`.github/workflows/tests.yml`) runs the full test suite on every push and pull request to `main`.

---

## Prerequisites

Software required to run the project locally:

- Python 3.10+
- PostgreSQL
- Essential packages listed in `requirements.txt`
- Environment file configured (`.env`)

Alternatively, run everything with Docker (see [Running with Docker](#running-with-docker)) — only Docker, Docker Compose and a configured `.env` are required, with no local Python or PostgreSQL install.

---

## Running Project

Clone the repository:

```bash
git clone https://github.com/AntonioAugustof/sga-api-pipeline.git
cd sga-api-pipeline
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure your environment variables — create a `.env` file in the root directory:

```env
API_BASE_URL=https://your-api-url.com
API_KEY=your_api_key
SYSTEM_USER=your_system_user
SYSTEM_PASSWORD=your_system_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password
# Optional: Discord webhook for failure alerts (skipped if unset)
DISCORD_WEBHOOK_URL=
```

Run the full pipeline:

```bash
python -m orchestrators.run_pipeline
```

Or run individual stages:

```bash
python -m extract.extract_volunteers
python -m transform.transform_volunteers
python -m load.load_dimensions
```

Modules must be run with `python -m` **from the repository root**: imports are absolute (`from infra.config import config`), so running a file by path (`python extract/extract_volunteers.py`) puts only that file's folder on `sys.path` and fails with `ModuleNotFoundError: No module named 'infra'`.

Run the tests:

```bash
pytest
```

---

## Running with Docker

The project ships with a `Dockerfile` and a `docker-compose.yml` that bring up the whole stack — the pipeline and its PostgreSQL database — reproducibly, with no local Python or PostgreSQL install required.

Prerequisites: Docker and Docker Compose, plus a configured `.env` (same variables as above).

Build and start the stack in the background:

```bash
docker compose up --build -d
```

This starts two services: `postgres` (PostgreSQL 18, on host port `5433` to avoid clashing with a local install on `5432`, data persisted in a named volume) and `pipeline` (the app, serving the Prefect schedule). Inside the compose network the app reaches the database at host `postgres` — Compose overrides `DB_HOST` accordingly, so the `.env` value is only used for non-Docker runs.

Useful commands:

```bash
docker compose ps                    # service status
docker compose logs -f pipeline      # follow the pipeline logs
docker compose down                  # stop the stack (keeps the database volume)
docker compose down -v               # stop and delete the database volume
```

The containerized database starts empty and is repopulated by the pipeline on its next run. To seed it with an existing database instead, restore a dump into the `postgres` service:

```bash
docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" < your_dump.sql
```

---

## Scheduling

The pipeline runs unattended as a daily Prefect flow. `orchestrators/serve.py` registers a cron schedule (03:00, `America/Sao_Paulo`) and serves the deployment:

```bash
python -m orchestrators.serve
```

This process must stay alive to fire the schedule. In production it runs as a Windows service (via NSSM), so it survives reboots and no terminal needs to stay open. Optionally, `prefect server start` exposes a local UI at `http://localhost:4200` for run history and monitoring.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

## Contact

Please feel free to contact me if you have any questions.

Antonio Augusto - @AntonioAugustoF
