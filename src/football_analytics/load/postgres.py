import argparse
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from football_analytics.config.settings import (
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
)


TABLE_LOAD_ORDER = [
    "dates",
    "teams",
    "venues",
    "players",
    "team_seasons",
    "fixtures",
    "fixture_team_results",
    "player_season_stats",
]

DATE_COLUMNS = {
    "dates": ["Date"],
    "players": ["BirthDate"],
    "fixtures": ["FixtureDateUTC", "FixtureDate"],
}


def _to_snake_case(value: str):
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = value.replace(" ", "_").replace("-", "_")
    value = re.sub(r"[^a-zA-Z0-9_]", "", value)
    value = re.sub(r"_+", "_", value)
    return value.lower().strip("_")


def build_engine():
    if not DB_PASSWORD:
        raise ValueError(
            "DB_PASSWORD não está configurado. "
            "Adicione a senha do PostgreSQL no arquivo .env."
        )

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
    )

    return create_engine(url)


def _read_stage_csv(table_name: str, stage_dir: str):
    filepath = Path(stage_dir) / f"{table_name}.csv"

    if not filepath.exists():
        raise FileNotFoundError(f"Arquivo stage não encontrado: {filepath}")

    df = pd.read_csv(filepath)

    for column in DATE_COLUMNS.get(table_name, []):
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    df.columns = [_to_snake_case(column) for column in df.columns]

    return df


def load_stage_to_postgres(
    stage_dir: str = "data/stage",
    schema: str = "stage",
    if_exists: str = "replace",
):
    engine = build_engine()
    loaded_tables = {}

    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    for table_name in TABLE_LOAD_ORDER:
        df = _read_stage_csv(table_name, stage_dir)

        df.to_sql(
            table_name,
            engine,
            schema=schema,
            if_exists=if_exists,
            index=False,
            chunksize=1000,
            method="multi",
        )

        loaded_tables[table_name] = len(df)
        print(f"{schema}.{table_name}: {len(df)} linhas carregadas.")

    return loaded_tables


def load_processed_to_postgres(
    processed_dir: str = "data/stage",
    schema: str = "stage",
    if_exists: str = "replace",
):
    """Backward-compatible alias for older calls."""

    return load_stage_to_postgres(
        stage_dir=processed_dir,
        schema=schema,
        if_exists=if_exists,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Carrega os CSVs de stage no PostgreSQL."
    )
    parser.add_argument("--stage-dir", default="data/stage")
    parser.add_argument("--schema", default="stage")
    parser.add_argument(
        "--if-exists",
        default="replace",
        choices=["fail", "replace", "append"],
        help="Comportamento caso a tabela já exista.",
    )
    args = parser.parse_args()

    load_stage_to_postgres(
        stage_dir=args.stage_dir,
        schema=args.schema,
        if_exists=args.if_exists,
    )
