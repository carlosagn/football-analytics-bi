import argparse
import re

from sqlalchemy import text

from football_analytics.load.etl import (
    ensure_etl,
    finish_run,
    require_mutable_season,
    start_run,
)
from football_analytics.load.postgres import _to_snake_case, build_engine
from football_analytics.transform.all import transform_all


TABLE_KEYS = {
    "dates": ["date_key"],
    "teams": ["team_id"],
    "venues": ["venue_id"],
    "players": ["player_id"],
}

SEASON_TABLES = [
    "team_seasons",
    "fixtures",
    "fixture_team_results",
    "player_season_stats",
]

LOAD_ORDER = [
    "dates",
    "teams",
    "venues",
    "players",
    "team_seasons",
    "fixtures",
    "fixture_team_results",
    "player_season_stats",
]


def _validate_identifier(value):
    if not re.match(r"^[a-z][a-z0-9_]*$", value):
        raise ValueError(f"Identificador SQL inválido: {value}")
    return value


def _prepare_frames(season):
    frames = transform_all(season=season)

    for table_name, frame in frames.items():
        if frame.empty:
            raise ValueError(
                f"Transformação de {table_name} ficou vazia para {season}."
            )
        frame.columns = [_to_snake_case(column) for column in frame.columns]

    for table_name in SEASON_TABLES:
        values = set(frames[table_name]["season"].dropna().astype(int))
        if values != {season}:
            raise ValueError(
                f"{table_name} contém temporadas inesperadas: {sorted(values)}"
            )

    for table_name, keys in TABLE_KEYS.items():
        if frames[table_name].duplicated(subset=keys).any():
            raise ValueError(f"Chave duplicada em {table_name}: {keys}")

    return frames


def refresh_stage_season(season, force=False, work_schema=None):
    engine = build_engine()
    run_id = None
    work_schema = _validate_identifier(
        work_schema or f"stage_work_{season}"
    )

    try:
        with engine.begin() as connection:
            ensure_etl(connection)
            require_mutable_season(connection, season, force=force)
            run_id = start_run(connection, season, "stage_incremental")

        frames = _prepare_frames(season)

        with engine.begin() as connection:
            connection.execute(
                text(f'DROP SCHEMA IF EXISTS "{work_schema}" CASCADE')
            )
            connection.execute(text(f'CREATE SCHEMA "{work_schema}"'))
            for table_name in LOAD_ORDER:
                connection.execute(
                    text(
                        f'CREATE TABLE "{work_schema}"."{table_name}" '
                        f'(LIKE stage."{table_name}" INCLUDING DEFAULTS)'
                    )
                )

        for table_name in LOAD_ORDER:
            frames[table_name].to_sql(
                table_name,
                engine,
                schema=work_schema,
                if_exists="append",
                index=False,
                chunksize=1000,
                method="multi",
            )

        with engine.begin() as connection:
            for table_name, keys in TABLE_KEYS.items():
                condition = " AND ".join(
                    f't."{key}" = w."{key}"' for key in keys
                )
                connection.execute(
                    text(
                        f'DELETE FROM stage."{table_name}" t '
                        f'USING "{work_schema}"."{table_name}" w '
                        f"WHERE {condition}"
                    )
                )

            for table_name in SEASON_TABLES:
                connection.execute(
                    text(
                        f'DELETE FROM stage."{table_name}" '
                        "WHERE season = :season"
                    ),
                    {"season": season},
                )

            for table_name in LOAD_ORDER:
                connection.execute(
                    text(
                        f'INSERT INTO stage."{table_name}" '
                        f'SELECT * FROM "{work_schema}"."{table_name}"'
                    )
                )

            connection.execute(
                text(f'DROP SCHEMA "{work_schema}" CASCADE')
            )

        row_counts = {
            name: len(frame) for name, frame in frames.items()
        }
        finish_run(engine, run_id, "success", row_counts=row_counts)
        print(f"Stage atualizado somente para a temporada {season}.")
        return row_counts
    except Exception as exc:
        if run_id is not None:
            finish_run(engine, run_id, "failed", error_message=str(exc))
        with engine.begin() as connection:
            connection.execute(
                text(f'DROP SCHEMA IF EXISTS "{work_schema}" CASCADE')
            )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Atualiza somente uma temporada no schema stage."
    )
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    refresh_stage_season(args.season, force=args.force)
