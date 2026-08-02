"""Central configuration for Snowflake connection details and data file paths.

Loads Snowflake credentials from `.env` (never hardcoded, never committed)
and exposes the repo's canonical source-file paths so ingestion scripts
never hardcode a filename.
"""

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent

MATCH_SOURCE_PATH = REPO_ROOT / "data" / "processed" / "wc2026_stage_mapping.csv"
SHOOTOUT_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "shootouts_full.csv"
GROUP_DRAW_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "wc2026_group_draw.csv"
CONFEDERATION_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "wc2026_confederation_map.csv"
VENUE_COORDINATES_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "wc2026_venue_coordinates.csv"
INTERNATIONAL_RESULTS_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "international_results_full.csv"
HISTORICAL_MATCH_SOURCE_PATH = REPO_ROOT / "data" / "processed" / "wc_historical_matches.csv"
HISTORICAL_CONFEDERATION_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "wc_historical_confederation_map.csv"
FIFA_RANKING_SOURCE_PATH = REPO_ROOT / "data" / "raw" / "wc_fifa_ranking_snapshots.csv"


@dataclass(frozen=True)
class SnowflakeConfig:
    """Snowflake connection parameters, read from environment variables."""

    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str
    schema: str


def get_required_env(name: str) -> str:
    """Return the named environment variable or raise if it is missing."""
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_snowflake_config() -> SnowflakeConfig:
    """Build a SnowflakeConfig from environment variables loaded from .env."""
    return SnowflakeConfig(
        account=get_required_env("SNOWFLAKE_ACCOUNT"),
        user=get_required_env("SNOWFLAKE_USER"),
        password=get_required_env("SNOWFLAKE_PASSWORD"),
        role=get_required_env("SNOWFLAKE_ROLE"),
        warehouse=get_required_env("SNOWFLAKE_WAREHOUSE"),
        database=get_required_env("SNOWFLAKE_DATABASE"),
        schema=get_required_env("SNOWFLAKE_SCHEMA"),
    )


def load_secondary_snowflake_config() -> SnowflakeConfig:
    """Build a SnowflakeConfig for Build 9's secondary (consumer) trial account."""
    return SnowflakeConfig(
        account=get_required_env("SNOWFLAKE_SECONDARY_ACCOUNT"),
        user=get_required_env("SNOWFLAKE_SECONDARY_USER"),
        password=get_required_env("SNOWFLAKE_SECONDARY_PASSWORD"),
        role=get_required_env("SNOWFLAKE_SECONDARY_ROLE"),
        warehouse=get_required_env("SNOWFLAKE_SECONDARY_WAREHOUSE"),
        database=get_required_env("SNOWFLAKE_SECONDARY_DATABASE"),
        schema=get_required_env("SNOWFLAKE_SECONDARY_SCHEMA"),
    )
