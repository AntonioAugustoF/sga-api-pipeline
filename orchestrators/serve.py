from prefect.client.schemas.schedules import CronSchedule
from orchestrators.run_pipeline import run_pipeline


if __name__ == "__main__":
    run_pipeline.serve(
        name="sga-diario",
        schedule=CronSchedule(
            cron="0 3 * * *",
            timezone="America/Sao_Paulo",
        ),
    )