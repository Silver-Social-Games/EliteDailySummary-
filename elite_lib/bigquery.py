"""Shared BigQuery client and canonical Elite-book SQL."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "silver-social-games-data"


def _local_default_key() -> Path | None:
    """Optional machine-local credentials path — never committed to git.

    To avoid setting GOOGLE_APPLICATION_CREDENTIALS every session, create
    elite_lib/_local_credentials.py (gitignored) with:

        DEFAULT_KEY_PATH = r"C:\\path\\to\\your\\key.json"
    """
    try:
        from elite_lib._local_credentials import DEFAULT_KEY_PATH  # type: ignore
    except ImportError:
        return None
    return Path(DEFAULT_KEY_PATH)


def get_client() -> bigquery.Client:
    """Create an EU BigQuery client from env credentials, a local override, or ADC."""
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    key_path = Path(env_path) if env_path else _local_default_key()
    if key_path is not None and key_path.exists():
        credentials = service_account.Credentials.from_service_account_file(
            str(key_path),
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        return bigquery.Client(
            project=PROJECT_ID,
            credentials=credentials,
            location="EU",
        )
    return bigquery.Client(project=PROJECT_ID, location="EU")


def run_query(client: bigquery.Client, sql: str) -> list[dict]:
    """Execute SQL and return rows as plain dictionaries."""
    return [dict(row.items()) for row in client.query(sql).result()]


def run_query_params(
    client: bigquery.Client,
    sql: str,
    query_parameters: Sequence[bigquery.ScalarQueryParameter],
    *,
    maximum_bytes_billed: int | None = 2_000_000_000,
    timeout: float = 60,
) -> list[dict]:
    """Execute parameterized SQL with an optional scan limit."""
    job_config = bigquery.QueryJobConfig(
        query_parameters=list(query_parameters),
        use_query_cache=True,
    )
    if maximum_bytes_billed is not None:
        job_config.maximum_bytes_billed = maximum_bytes_billed
    rows = client.query(sql, job_config=job_config).result(timeout=timeout)
    return [dict(row.items()) for row in rows]


def dashboard_elite_ctes(
    *,
    latest_name: str = "latest_elite_tag_snapshot",
    elite_name: str = "elite_accounts",
    aid_alias: str = "AID",
    agent_alias: str = "agent",
) -> str:
    """Return canonical dashboard-book and latest-agent CTEs.

    The revenue book is dbt_aninditac.elite. The tag mart supplies the current
    agent label but never replaces the dashboard book filter.
    """
    return f"""
{latest_name} AS (
  SELECT MAX(snapshot_date) AS snapshot_date
  FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
),
{elite_name} AS (
  SELECT DISTINCT
    e.account_id AS {aid_alias},
    COALESCE(t.tag_agent_1, e.agent_name) AS {agent_alias}
  FROM `{PROJECT_ID}.dbt_aninditac.elite` e
  CROSS JOIN {latest_name} l
  LEFT JOIN `{PROJECT_ID}.dbt_utils.elite_account_tags` t
    ON e.account_id = t.account_id
    AND t.snapshot_date = l.snapshot_date
    AND t.category = 'Elite'
    AND t.tag_agent_1 IS NOT NULL
)
""".strip()


def latest_elite_tags_cte(
    *,
    cte_name: str = "latest_elite_tags",
    require_agent: bool = False,
) -> str:
    """Return the latest Elite tag snapshot for labels and roster filtering."""
    agent_filter = "AND et.tag_agent_1 IS NOT NULL" if require_agent else ""
    return f"""
{cte_name} AS (
  SELECT et.account_id, et.tag_agent_1
  FROM `{PROJECT_ID}.dbt_utils.elite_account_tags` et
  CROSS JOIN (
    SELECT MAX(snapshot_date) AS snapshot_date
    FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
  ) latest
  WHERE et.snapshot_date = latest.snapshot_date
    AND et.category = 'Elite'
    {agent_filter}
)
""".strip()
