from orchestrators.run_pipeline import run_pipeline


if __name__ == "__main__":
    run_pipeline.serve(
        name="sga-diario",
        cron="0 3 * * *", # everyday at 3 a.m.
    )