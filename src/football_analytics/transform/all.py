from pathlib import Path

from football_analytics.transform.fixtures import (
    transform_dates,
    transform_fixture_team_results,
    transform_fixtures,
)
from football_analytics.transform.players import (
    transform_player_season_stats,
    transform_players,
)
from football_analytics.transform.teams import (
    transform_team_seasons,
    transform_teams,
    transform_venues,
)


OUTPUTS = {
    "teams": transform_teams,
    "venues": transform_venues,
    "players": transform_players,
    "dates": transform_dates,
    "team_seasons": transform_team_seasons,
    "fixtures": transform_fixtures,
    "fixture_team_results": transform_fixture_team_results,
    "player_season_stats": transform_player_season_stats,
}


def run_all(output_dir: str = "data/stage"):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {}

    for name, transform in OUTPUTS.items():
        df = transform()
        filepath = output_path / f"{name}.csv"
        df.to_csv(filepath, index=False, encoding="utf-8")
        results[name] = {
            "rows": len(df),
            "columns": len(df.columns),
            "file": str(filepath),
        }
        print(
            f"{name}: {len(df)} linhas, {len(df.columns)} colunas -> {filepath}"
        )

    return results


if __name__ == "__main__":
    run_all()
