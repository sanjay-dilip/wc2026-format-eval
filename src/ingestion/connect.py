"""Snowflake connection helper, built on config.py's SnowflakeConfig."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import snowflake.connector
from snowflake.connector import SnowflakeConnection

from config import load_snowflake_config


def get_connection() -> SnowflakeConnection:
    """Open a Snowflake connection using credentials from .env."""
    cfg = load_snowflake_config()
    return snowflake.connector.connect(
        account=cfg.account,
        user=cfg.user,
        password=cfg.password,
        role=cfg.role,
        warehouse=cfg.warehouse,
        database=cfg.database,
        schema=cfg.schema,
    )
