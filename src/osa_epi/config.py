import os
from pathlib import Path


def _resolve_project_root() -> Path:
    if env_root := os.getenv("OSA_EPI_ROOT"):
        return Path(env_root).resolve()

    cwd = Path.cwd()
    if (cwd / "sql").is_dir():
        return cwd

    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = _resolve_project_root()
SQL_DIR = PROJECT_ROOT / "sql"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
TABLES_DIR = OUTPUTS_DIR / "tables"
FIGURES_DIR = OUTPUTS_DIR / "figures"

DEFAULT_COHORT_ID = int(os.getenv("DEFAULT_COHORT_ID", "2"))
