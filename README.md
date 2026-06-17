# Data Engineering Project - SGA API Pipeline

This repository contains the implementation of a data pipeline (SGA API Pipeline) designed to extract, transform, and load data efficiently, ensuring data consistency and reliability for downstream analysis and reporting.

The pipeline architecture is built using modular Python scripts and industry-standard practices for clean, scalable data engineering.

Access structured and cleaned data ready for consumption. 💪

---

## Table of Contents

- [Architecture & Folder Structure](#architecture--folder-structure)
- [How It Works](#how-it-works)
  - [Data Extraction](#data-extraction)
  - [Data Transformation](#data-transformation)
  - [Data Load](#data-load)
  - [Infrastructure & Orchestration](#infrastructure--orchestration)
- [Entities](#entities)
- [Prerequisites](#prerequisites)
- [Running Project](#running-project)
- [License](#license)
- [Contact](#contact)

---

## Architecture & Folder Structure

The project follows a rigorous separation of concerns to ensure maintainability:

```
sga-api-pipeline/
├── data/
│   ├── raw/            # Raw JSON files extracted from the API
│   └── processed/      # Cleaned Parquet files ready for loading
├── extract/            # Extraction scripts (API connectors)
├── infra/              # Infrastructure configurations and database connections
├── load/               # Loading modules (PostgreSQL insertions)
├── logs/               # Application and pipeline execution logs
├── orchestrators/      # Pipeline automation and scheduling scripts
└── transform/          # Data cleaning, processing, and business logic (Pandas)
```

---

## How It Works

### Data Extraction

The modules inside the `/extract` folder are responsible for connecting to the SGA API. They fetch data in paginated batches across all available statuses, ensuring connection security through environment variables (`.env`). Raw data is saved as JSON files in `data/raw/`.

Invoices use a multi-window incremental strategy (by emission, payment, and due date) to capture new and recently changed records. Delinquency uses a full-history extract — querying only `status=2` (open) with no date filter — to ensure no overdue invoice is missed regardless of when it was issued.

### Data Transformation

Inside the `/transform` folder, data undergoes rigorous cleaning and structuring:

- Data type casting and formatting.
- Handling missing values and duplicates.
- Serialization of nested fields (arrays and dictionaries).
- History tracking for entities with status changes (Customers and Vehicles).

Cleaned data is saved as Parquet files in `data/processed/`.

### Data Load

The `/load` folder safely writes processed data into PostgreSQL using three strategies:

| Strategy | Tables | Behavior |
|---|---|---|
| Replace | Dimension tables | Always reflects current state |
| Upsert | `fact_invoices` | Inserts new records; updates existing ones by `codigo_boleto` |
| Snapshot append | `fact_delinquency_snapshot` | Appends a dated slice of open invoices daily; re-runs on the same day are idempotent (previous slice is replaced) |

### Infrastructure & Orchestration

**Infrastructure (`/infra`):** Manages database connection pools, API authentication, and environment configuration.

**Orchestration (`/orchestrators`):** Triggers the execution flow of the ETL phases (Extract → Transform → Load) in the correct sequence.

---

## Entities

| Entity | Table | Notes |
|---|---|---|
| Volunteers | `dim_volunteers` | — |
| Cooperatives | `dim_cooperatives` | — |
| Regionals | `dim_regionals` | — |
| Customers | `dim_customers` | History tracked in `dim_customers_history` |
| Vehicles | `dim_vehicles` | History tracked in `dim_vehicles_history` |
| Invoices | `fact_invoices` | Incremental upsert; multi-window extraction |
| Delinquency | `fact_delinquency_snapshot` | Daily snapshot of all open invoices (`status=2`) |

---

## Prerequisites

Software required to run the project locally:

- Python 3.10+
- PostgreSQL
- Essential packages listed in `requirements.txt`
- Environment file configured (`.env`)

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

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

## Contact

Please feel free to contact me if you have any questions.

Antonio Augusto - @AntonioAugustoF