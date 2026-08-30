# Current architecture

The pipeline as it stands **after the cutover**, on 2026-08-29. There is one
path: Python extracts, dbt does everything else. The pandas path that ran
alongside it for eleven days was deleted once the two agreed row by row — see
[`ROADMAP.md`](../ROADMAP.md).

---

## 1. The whole picture

```mermaid
flowchart TB
    API(["SGA API"])

    subgraph EXTRACT["extract/ · Python"]
        EX["8 extractors<br/><i>authenticate, paginate, retry</i>"]
    end

    API --> EX
    EX -->|"jsonb, append-only"| RAW[("<b>raw</b><br/>9 tables")]

    subgraph NEW["dbt · 23 models, 2 snapshots, 31 tests"]
        RAW --> STG["<b>staging</b><br/>9 views"]
        STG --> SNP["<b>snapshots</b><br/>SCD2, 2 tables"]
        STG --> INT["<b>intermediate</b><br/>2 views"]
        SNP --> MRT["<b>marts</b><br/>12 models"]
        INT --> MRT
        STG --> MRT
    end

    MRT --> ANA[("<b>analytics</b><br/>star schema")]
    ANA ==> BI(["Power BI"])

    classDef new fill:#e8f5e9,stroke:#2e7d32
    class NEW,ANA,RAW new
```

**What to read out of it.** Python has exactly one job, and it is the one job
that cannot be done in SQL: talking to something outside this machine.
Everything downstream is versioned SQL, tested on every run, rebuildable from
what the API actually returned.

---

## 2. Inside dbt

```mermaid
flowchart LR
    subgraph SRC["raw"]
        R1[("regionals")]
        R2[("cooperatives<br/>statuses<br/>invoice_statuses<br/>volunteers")]
        R3[("vehicles<br/>customers")]
        R4[("invoices<br/>delinquency")]
    end

    subgraph STG["staging · views"]
        S1["stg_sga__regionals"]
        S2["stg_sga__cooperatives<br/>stg_sga__statuses<br/>stg_sga__invoice_statuses<br/>stg_sga__volunteers"]
        S3["stg_sga__vehicles<br/>stg_sga__customers"]
        S4["stg_sga__invoices<br/>stg_sga__delinquency"]
    end

    subgraph SNAP["snapshots · SCD2"]
        N1["snap_vehicles"]
        N2["snap_customers"]
    end

    subgraph MART["marts"]
        D1["dim_regionals"]
        D2["dim_cooperatives · dim_status<br/>dim_status_invoice · dim_volunteers"]
        D3["dim_vehicles · dim_customers"]
        F1["fact_invoices"]
        F2["bridge_invoices_vehicles"]
        F3["fact_delinquency_snapshot"]
        M1["mart_delinquency_current<br/>mart_delinquency_point_in_time"]
    end

    R1 --> S1 --> D1
    R2 --> S2 --> D2
    R3 --> S3
    S3 --> N1 --> D3
    S3 --> N2 --> D3
    R4 --> S4
    S4 --> F1
    S4 --> F2
    S4 --> F3
    D3 -.->|"point-in-time<br/>surrogate key"| F1
    D3 -.-> F3
    F3 --> M1
    F2 --> M1
    D3 --> M1
```

Four materialisation choices, each for a reason:

| Layer | Materialised as | Why |
|---|---|---|
| `staging` | view | Cheap to rebuild, always reads the latest batch |
| `snap_*` | snapshot | dbt manages `dbt_valid_from` / `dbt_valid_to` in one MERGE |
| `dim_vehicles`, `dim_customers` | table | Rebuilt in full from the snapshots every run |
| everything else in `marts` | **incremental** | They *accumulate* — see below |

---

## 3. Why the facts are incremental

The single most consequential thing to understand about this pipeline.

```mermaid
flowchart LR
    A["API returns only<br/>what is new, paid<br/>or rescheduled"] --> B["raw holds<br/>a week of invoices"]
    B --> C{"materialise<br/>as what?"}
    C -->|"table"| D["316,918 → 7,580<br/><b>98% of revenue history lost</b><br/>every test still green"]
    C -->|"incremental<br/>+ transplant"| E["318,182 invoices<br/>history preserved,<br/>new batches merged"]

    classDef bad fill:#ffebee,stroke:#c62828
    classDef good fill:#e8f5e9,stroke:#2e7d32
    class D bad
    class E good
```

The same applies to `bridge_invoices_vehicles` (384,242 rows), to
`fact_delinquency_snapshot` (43 daily photographs) and to the SCD2 history
(34,652 versions). None can be rebuilt from the source: the API answers about
the present, and yesterday's answer is gone unless it was stored.

That history was seeded once by the migrations under
[`sql/migrations/`](../sql/migrations/), and it is why `--full-refresh` and
`dbt build --empty` must never touch the real warehouse.

---

## 4. What runs on a schedule

```mermaid
flowchart LR
    subgraph P["Prefect · 03:00 daily"]
        F["extract → dbt build"]
    end
    subgraph W["Windows Task Scheduler"]
        FR["SGA-Freshness-Check<br/>06:00 daily"]
        BK["SGA-Warehouse-Backup<br/>Sundays 05:00"]
    end

    F --> ANA[("analytics")]
    FR -.->|"reads"| ANA
    FR -.->|"alerts if stale"| DIS(["Discord"])
    F -.->|"on failure"| DIS
    BK -->|"dump + verified restore"| DISK[["C:\backups\"]]
```

dbt runs **inside** the flow, not beside it. While it ran on demand, three days
of drift collapsed fifty-nine SCD2 transitions into a single date; a warehouse
written last night compared against one written last week measures the
schedule, not the models. A failing dbt node — a test included — stops the run.

Two things run **outside** the orchestrator, also on purpose.
`infra/freshness.py` is the dead-man's switch: it detects that the pipeline did
not run at all, which no alert inside the pipeline can do.
`scripts/backup_warehouse.py` follows the same logic — a backup that runs only
when the pipeline runs fails exactly when it is needed.

---

## 5. What the cutover removed

```mermaid
flowchart TB
    subgraph GO["deleted"]
        X1["transform/ · 9 modules"]
        X2["load/ · 5 modules"]
        X3["infra: loader, transformations,<br/>identifiers, sync_table_schema"]
        X4["22 reconciliation tests<br/>+ 4 macros + the warehouse source"]
        X5["data/raw/*.json writes"]
        X6["sql/ddl/000_baseline.sql"]
    end
    subgraph STAY["kept"]
        Y1["extract/ · lands raw only"]
        Y2["dbt · the whole warehouse"]
        Y3["infra/ · config, alerts, freshness,<br/>raw_writer, dbt_runner"]
        Y4["public · no longer written,<br/>not yet dropped"]
    end

    GO -.->|"Power BI repointed first"| STAY

    classDef bad fill:#ffebee,stroke:#c62828
    classDef good fill:#e8f5e9,stroke:#2e7d32
    class GO bad
    class STAY good
```

The reconciliation tests went too, and that is the uncomfortable part: they
existed to compare against `public`, so they became meaningless the moment
`public` did. What replaced them is not another comparison but the seven
singular tests and the schema tests that run against real rows every night —
and, before any of it, a backup that is restored and counted rather than merely
written.

`public` is still there, holding the last state the pandas path wrote. Nothing
reads it and nothing writes it. Dropping it is a decision for a calmer day.
