import argparse

from football_analytics.load.stage_incremental import refresh_stage_season
from football_analytics.load.warehouse_incremental import (
    refresh_warehouse_season,
)


def refresh_season(season, force=False):
    stage_counts = refresh_stage_season(season, force=force)
    warehouse_counts = refresh_warehouse_season(season, force=force)
    print(f"Temporada {season} atualizada com sucesso do raw ao warehouse.")
    return {
        "stage": stage_counts,
        "warehouse": warehouse_counts,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Transforma o raw existente e atualiza stage e warehouse "
            "somente para uma temporada. Não chama a API."
        )
    )
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    refresh_season(args.season, force=args.force)
