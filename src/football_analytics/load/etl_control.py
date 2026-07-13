import argparse
import json

from sqlalchemy import text

from football_analytics.config.constants import SUPPORTED_SEASONS
from football_analytics.load.postgres import build_engine


ETL_CONTROL_SQL = [
    "CREATE SCHEMA IF NOT EXISTS etl",
    """
    CREATE TABLE IF NOT EXISTS etl.season_control (
        season INTEGER PRIMARY KEY,
        status VARCHAR(10) NOT NULL CHECK (status IN ('active', 'closed')),
        activated_at TIMESTAMP,
        closed_at TIMESTAMP,
        last_successful_run_at TIMESTAMP
    )
    """,
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


def ensure_etl_control(connection):
    for statement in ETL_CONTROL_SQL:
        connection.execute(text(statement))

    for season in SUPPORTED_SEASONS:
        connection.execute(
            text(
                """
                INSERT INTO etl.season_control (season, status)
                VALUES (:season, 'closed')
                ON CONFLICT (season) DO NOTHING
                """
            ),
            {"season": season},
        )


def require_active_season(connection, season, force=False):
    status = connection.execute(
        text("SELECT status FROM etl.season_control WHERE season = :season"),
        {"season": season},
    ).scalar()

    if status is None:
        raise ValueError(
            f"Temporada {season} não cadastrada em etl.season_control. "
            "Ative-a explicitamente antes da primeira carga."
        )
    if status != "active" and not force:
        raise ValueError(
            f"Temporada {season} está com status '{status}'. "
            "Use --force somente para uma correção histórica intencional."
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


def set_season_status(season, status):
    if status not in {"active", "closed"}:
        raise ValueError("Status deve ser 'active' ou 'closed'.")

    engine = build_engine()
    with engine.begin() as connection:
        ensure_etl_control(connection)
        connection.execute(
            text(
                """
                INSERT INTO etl.season_control (
                    season, status, activated_at, closed_at
                )
                VALUES (
                    :season,
                    :status,
                    CASE WHEN :status = 'active' THEN CURRENT_TIMESTAMP END,
                    CASE WHEN :status = 'closed' THEN CURRENT_TIMESTAMP END
                )
                ON CONFLICT (season) DO UPDATE SET
                    status = EXCLUDED.status,
                    activated_at = CASE
                        WHEN EXCLUDED.status = 'active' THEN CURRENT_TIMESTAMP
                        ELSE etl.season_control.activated_at
                    END,
                    closed_at = CASE
                        WHEN EXCLUDED.status = 'closed' THEN CURRENT_TIMESTAMP
                        ELSE NULL
                    END
                """
            ),
            {"season": season, "status": status},
        )

    print(f"Temporada {season} marcada como {status}.")


def list_seasons():
    engine = build_engine()
    with engine.begin() as connection:
        ensure_etl_control(connection)
        rows = connection.execute(
            text(
                """
                SELECT season, status, activated_at, closed_at,
                       last_successful_run_at
                FROM etl.season_control
                ORDER BY season
                """
            )
        ).fetchall()

    for row in rows:
        print(*row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Controle operacional do ETL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list")
    activate = subparsers.add_parser("activate")
    activate.add_argument("--season", type=int, required=True)
    args = parser.parse_args()

    if args.command == "list":
        list_seasons()
    elif args.command == "activate":
        set_season_status(args.season, "active")
