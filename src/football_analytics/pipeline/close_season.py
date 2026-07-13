import argparse

from sqlalchemy import text

from football_analytics.load.etl_control import set_season_status
from football_analytics.load.postgres import build_engine
from football_analytics.pipeline.refresh_season import refresh_season


FINAL_STATUSES = {"FT", "AET", "PEN", "CANC"}


def close_season(season):
    refresh_season(season)

    engine = build_engine()
    with engine.connect() as connection:
        pending = connection.execute(
            text(
                """
                SELECT status_short, COUNT(*)
                FROM stage.fixtures
                WHERE season = :season
                  AND status_short NOT IN ('FT', 'AET', 'PEN', 'CANC')
                GROUP BY status_short
                ORDER BY status_short
                """
            ),
            {"season": season},
        ).fetchall()

    if pending:
        raise ValueError(
            f"Temporada {season} ainda possui partidas não finalizadas: "
            f"{[tuple(row) for row in pending]}"
        )

    set_season_status(season, "closed")
    print(f"Temporada {season} finalizada e protegida contra novas cargas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executa a carga final e encerra uma temporada ativa."
    )
    parser.add_argument("--season", type=int, required=True)
    args = parser.parse_args()
    close_season(args.season)
