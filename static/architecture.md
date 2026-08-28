# Current architecture

A snapshot of the pipeline as it stands **mid-migration**, on 2026-08-26. Two
paths run in parallel over the same warehouse: the original pandas path, which
still serves Power BI, and the dbt path, which reproduces it from a raw layer.
Neither is removed until the other is proven — see [`ROADMAP.md`](../ROADMAP.md).

---

## 1. The whole picture

```mermaid
flowchart TB
    API(["SGA API"])

    subgraph EXTRACT["extract/ · Python"]
        EX["8 extractors<br/><i>authenticate, paginate, retry</i>"]
    end

    API --> EX
    EX -->|"JSON files"| FILES[["data/raw/*.json"]]
    EX -->|"jsonb, append-only"| RAW[("<b>raw</b><br/>9 tables")]

    subgraph OLD["pandas path — to be removed in phase 5"]
        FILES --> TR["transform/<br/><i>business rules</i>"]
        TR --> PARQ[["data/processed/*.parquet"]]
        PARQ --> LD["load/<br/><i>upserts, hand-rolled SCD2</i>"]
    end

    LD --> PUB[("<b>public</b><br/>10 tables")]

    subgraph NEW["dbt"]
        RAW --> STG["<b>staging</b><br/>8 views"]
        STG --> SNP["<b>snapshots</b><br/>SCD2, 2 tables"]
        STG --> INT["<b>intermediate</b><br/>2 views"]
        SNP --> MRT["<b>marts</b><br/>11 models"]
        INT --> MRT
        STG --> MRT
    end

    MRT --> ANA[("<b>analytics</b><br/>11 tables + views")]

    ANA -.->|"28 reconciliation tests<br/>compare row by row"| PUB
    PUB ==>|"still reads here"| BI(["Power BI"])

    classDef old fill:#fff3e0,stroke:#e65100
    classDef new fill:#e8f5e9,stroke:#2e7d32
    class OLD,PUB old
    class NEW,ANA,RAW new
```

**What to read out of it.** Extraction writes to two places. The file feeds the
path that still serves the business; the jsonb feeds the path that will replace
it. Everything downstream is duplicated on purpose, and 28 singular tests hold
the two sides to the same answer on every build.

---

## 2. Inside dbt

```mermaid
flowchart LR
    subgraph SRC["raw"]
        R1[("regionals")]
        R2[("cooperatives<br/>statuses<br/>invoice_statuses")]
        R3[("vehicles<br/>customers")]
        R4[("invoices<br/>delinquency")]
    end

    subgraph STG["staging · views"]
        S1["stg_sga__regionals"]
        S2["stg_sga__cooperatives<br/>stg_sga__statuses<br/>stg_sga__invoice_statuses"]
        S3["stg_sga__vehicles<br/>stg_sga__customers"]
        S4["stg_sga__invoices<br/>stg_sga__delinquency"]
    end

    subgraph SNAP["snapshots · SCD2"]
        N1["snap_vehicles"]
        N2["snap_customers"]
    end

    subgraph MART["marts"]
        D1["dim_regionals"]
        D2["dim_cooperatives<br/>dim_status<br/>dim_status_invoice"]
        D3["dim_vehicles<br/>dim_customers"]
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

Three materialisation choices, each for a reason:

| Layer | Materialised as | Why |
|---|---|---|
| `staging` | view | Cheap to rebuild, always reads the latest batch |
| `dim_*` | table | Consumed by Power BI; a view would re-run the chain per visual |
| `snap_*` | snapshot | dbt manages `dbt_valid_from` / `dbt_valid_to` in one MERGE |
| `fact_*`, `bridge_*` | **incremental** | They *accumulate* — see below |

---

## 3. Why the facts are incremental

The single most consequential thing to understand about this pipeline.

```mermaid
flowchart LR
    A["API returns only<br/>what is new, paid<br/>or rescheduled"] --> B["raw holds<br/>7,580 invoices"]
    B --> C{"materialise<br/>as what?"}
    C -->|"table"| D["316,918 → 7,580<br/><b>98% of revenue history lost</b><br/>every test still green"]
    C -->|"incremental<br/>+ transplant"| E["316,924 invoices<br/>history preserved,<br/>new batches merged"]

    classDef bad fill:#ffebee,stroke:#c62828
    classDef good fill:#e8f5e9,stroke:#2e7d32
    class D bad
    class E good
```

The same applies to `bridge_invoices_vehicles` (382,761 rows), to
`fact_delinquency_snapshot` (39 daily photographs) and to the SCD2 history
(33,939 versions). None can be rebuilt from the source: the API answers about
the present, and yesterday's answer is gone unless it was stored.

That history was seeded once by the migrations under
[`sql/migrations/`](../sql/migrations/), and it is why `--full-refresh` and
`dbt build --empty` must never touch the real warehouse.

---

## 4. What runs on a schedule

```mermaid
flowchart LR
    subgraph P["Prefect · 03:00 daily"]
        F["extract → transform → load"]
    end
    subgraph W["Windows Task Scheduler"]
        FR["SGA-Freshness-Check<br/>06:00 daily"]
        BK["SGA-Warehouse-Backup<br/>Sundays 05:00"]
    end

    F --> PUB[("public")]
    FR -.->|"reads"| PUB
    FR -.->|"alerts if stale"| DIS(["Discord"])
    BK -->|"dump + verified restore"| DISK[["C:\backups\"]]

    NOTE["dbt is not scheduled yet.<br/>It runs on demand and in CI."]
    class NOTE note
```

Two things run **outside** the orchestrator on purpose. `infra/freshness.py` is
the dead-man's switch: it detects that the pipeline did not run at all, which no
alert inside the pipeline can do. `scripts/backup_warehouse.py` follows the same
logic — a backup that runs only when the pipeline runs fails exactly when it is
needed.

`dbt` is deliberately absent from this diagram: it has no schedule. Every PR
builds all 97 nodes against a throwaway PostgreSQL container in CI, but nothing
runs it daily against production. That is [issue #9](../../issues/9).

---

## 5. Known gap

`dim_volunteers` exists **only in `public`**. It was in the scope of phase 2 and
was never built in dbt — the phase was recorded as complete with three of its
four dimensions done. It is the one table that would be lost by deleting
`load/`, so it has to be migrated before the cutover can proceed.

```mermaid
flowchart LR
    subgraph OK["migrated · 11 relations"]
        A["dim_regionals · dim_cooperatives<br/>dim_status · dim_status_invoice<br/>dim_vehicles · dim_customers<br/>fact_invoices · bridge_invoices_vehicles<br/>fact_delinquency_snapshot<br/>snap_vehicles · snap_customers"]
    end
    subgraph GAP["not migrated"]
        B["dim_volunteers"]
    end
    classDef bad fill:#ffebee,stroke:#c62828
    class GAP,B bad
```

---

## 6. What phase 5 removes

```mermaid
flowchart TB
    subgraph GO["deleted"]
        X1["transform/ · 8 files"]
        X2["load/ · 5 files"]
        X3["infra.sync_table_schema"]
        X4["public schema"]
        X5["28 reconciliation tests"]
    end
    subgraph STAY["kept"]
        Y1["extract/ · lands raw only"]
        Y2["dbt · the whole warehouse"]
        Y3["infra/ · config, alerts,<br/>freshness, raw_writer"]
    end

    GO -.->|"Power BI repointed first,<br/>then a few days of waiting"| STAY

    classDef bad fill:#ffebee,stroke:#c62828
    classDef good fill:#e8f5e9,stroke:#2e7d32
    class GO bad
    class STAY good
```

The reconciliation tests go too, and that is the uncomfortable part: they exist
to compare against `public`, so they become meaningless the moment `public` does.
Everything they were protecting has to be protected by something else first —
which is why the backup was built before the cutover, not after.
