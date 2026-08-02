"""Snowflake connection helper, built on config.py's SnowflakeConfig."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import snowflake.connector
from snowflake.connector import SnowflakeConnection

from config import SnowflakeConfig, load_secondary_snowflake_config, load_snowflake_config


def _connect(cfg: SnowflakeConfig) -> SnowflakeConnection:
    """Open a Snowflake connection from a SnowflakeConfig."""
    return snowflake.connector.connect(
        account=cfg.account,
        user=cfg.user,
        password=cfg.password,
        role=cfg.role,
        warehouse=cfg.warehouse,
        database=cfg.database,
        schema=cfg.schema,
    )


def get_connection() -> SnowflakeConnection:
    """Open a Snowflake connection to the primary (producer) account using .env."""
    return _connect(load_snowflake_config())


def get_secondary_connection() -> SnowflakeConnection:
    """Open a Snowflake connection to Build 9's secondary (consumer) trial account."""
    return _connect(load_secondary_snowflake_config())
