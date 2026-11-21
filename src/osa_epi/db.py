import os
from pathlib import Path

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine

from osa_epi.config import PROJECT_ROOT, SQL_DIR


def get_engine(env_path: Path | None = None) -> Engine:
    """create a sqlalchemy postgresql engine from environment variables"""
    if env_path is not None:
        resolved_env = Path(env_path)
    else:
        cwd_env = find_dotenv(usecwd=True)
        resolved_env = Path(cwd_env) if cwd_env else (PROJECT_ROOT / ".env")
    load_dotenv(dotenv_path=resolved_env, override=True)
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    dbname = os.getenv("POSTGRES_DB")
    host = os.getenv("DB_HOST")
    port = int(os.getenv("DB_PORT"))

    missing = [
        name
        for name, val in (
            ("POSTGRES_USER", user),
            ("POSTGRES_PASSWORD", password),
            ("POSTGRES_DB", dbname),
        )
        if not val
    ]

    if missing:
        raise OSError(f"Missing required database variables: {', '.join(missing)}. ")

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=user,
        password=password,
        host=host,
        port=port,
        database=dbname,
    )
    return create_engine(url)


def execute_sql_script(
    engine: Engine,
    sql_filename: str,
    params: dict | None = None,
    sql_dir: Path = SQL_DIR,
) -> None:
    """Execute one or more statements from a .sql file"""
    script_path = sql_dir / sql_filename
    raw_sql = script_path.read_text(encoding="utf-8")
    statements = [stmt.strip() for stmt in raw_sql.split(";") if stmt.strip()]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt), params or {})


def run_sql_query(
    engine: Engine,
    sql_filename: str,
    params: dict | None = None,
    sql_dir: Path = SQL_DIR,
) -> pd.DataFrame:
    """Load a .sql file and return results as a dataframe"""
    query_path = sql_dir / sql_filename
    query = text(query_path.read_text(encoding="utf-8"))
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params or {})
