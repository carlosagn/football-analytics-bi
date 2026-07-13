import json

from sqlalchemy import text


ETL_SQL = [
    "CREATE SCHEMA IF NOT EXISTS etl",
    "DROP TABLE IF EXISTS etl.season_control",
    """
    CREATE TABLE IF NOT EXISTS etl.load_runs (
        run_id BIGSERIAL PRIMARY KEY,
        season INTEGER NOT NULL,
        load_type VARCHAR(40) NOT NULL,
        status VARCHAR(10) NOT NULL CHECK (
            status IN ('running', 'success', 'failed')
        ),
        started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP,
        row_counts JSONB,
        error_message TEXT
    )
    """,
]


def ensure_etl(connection):
    for statement in ETL_SQL:
        connection.execute(text(statement))


def require_mutable_season(connection, season, force=False):
    """Allow new/incomplete seasons and protect completed seasons."""

    warehouse_exists = connection.execute(
        text("SELECT to_regclass('warehouse.dim_season')")
    ).scalar()
    if warehouse_exists is None:
        return

    is_completed = connection.execute(
        text(
            """
            SELECT is_completed
            FROM warehouse.dim_season
            WHERE season_key = :season
            """
        ),
        {"season": season},
    ).scalar()

    if is_completed is True and not force:
        raise ValueError(
            f"Temporada {season} está concluída em "
            "warehouse.dim_season. Use --force somente para uma "
            "correção histórica intencional."
        )


def start_run(connection, season, load_type):
    return connection.execute(
        text(
            """
            INSERT INTO etl.load_runs (season, load_type, status)
            VALUES (:season, :load_type, 'running')
            RETURNING run_id
            """
        ),
        {"season": season, "load_type": load_type},
    ).scalar()


def finish_run(engine, run_id, status, row_counts=None, error_message=None):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE etl.load_runs
                SET status = :status,
                    finished_at = CURRENT_TIMESTAMP,
                    row_counts = CAST(:row_counts AS JSONB),
                    error_message = :error_message
                WHERE run_id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "status": status,
                "row_counts": json.dumps(row_counts or {}),
                "error_message": error_message,
            },
        )
