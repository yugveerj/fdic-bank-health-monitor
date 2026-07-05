"""The production pipeline as an explicit DAG: the three FDIC pulls run in
series so only one polite client talks to the API at a time, FRED lands
alongside, and dbt builds once both branches finish. Production
orchestration remains GitHub Actions cron (decisions.md) — this runs the
same ingestion code locally against an isolated raw dataset (compose sets
BQ_RAW_DATASET=airflow_raw)."""

from __future__ import annotations

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task


def _ingest(module_name: str) -> int:
    """Each task opens its own client and warehouse: Airflow tasks are
    separate processes, so nothing can be shared from a DAG-level scope."""
    import importlib

    from ingestion.bq import connect
    from ingestion.client import FdicClient

    module = importlib.import_module(f"ingestion.{module_name}")
    with FdicClient() as client:
        wh = connect()
        try:
            return module.ingest(client, wh)
        finally:
            wh.close()


@dag(
    dag_id="fdic_ingestion",
    schedule=None,  # triggered by hand; the real cadence lives in GitHub Actions
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["fdic"],
)
def fdic_ingestion():
    @task
    def institutions() -> int:
        return _ingest("fdic_institutions")

    @task
    def financials() -> int:
        return _ingest("fdic_financials")

    @task
    def failures() -> int:
        return _ingest("fdic_failures")

    @task
    def fred_h8() -> int:
        from ingestion import fred_h8 as fred
        from ingestion.bq import connect

        wh = connect()
        try:
            return fred.ingest(wh)
        finally:
            wh.close()

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="cd /opt/airflow/repo/dbt && dbt build --target dev",
    )

    fdic_chain = institutions() >> financials() >> failures()
    [fdic_chain, fred_h8()] >> dbt_build


fdic_ingestion()
