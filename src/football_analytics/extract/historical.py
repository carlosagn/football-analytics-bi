import argparse

from football_analytics.config.constants import (
    LEAGUE_SERIE_A,
    SUPPORTED_SEASONS,
)
from football_analytics.extract.fixtures import extract_fixtures
from football_analytics.extract.players import extract_players
from football_analytics.extract.teams import extract_teams


def _season_range(start_season: int, end_season: int):
    seasons = [
        season
        for season in SUPPORTED_SEASONS
        if start_season <= season <= end_season
    ]

    if not seasons:
        raise ValueError(
            f"Nenhuma temporada suportada entre {start_season} e {end_season}."
        )

    return seasons


def extract_historical_raw(
    league_id: int,
    start_season: int,
    end_season: int,
    include_players: bool = True,
    request_interval_seconds: float = 7,
    max_new_player_requests_per_season=None,
    max_pages_per_team=None,
):
    """Extract raw teams, fixtures and players across multiple seasons.

    Existing raw files are preserved and reused, so this command can be
    interrupted and safely resumed.
    """

    seasons = _season_range(start_season, end_season)
    summary = []

    print(
        f"Iniciando extração histórica: {seasons[0]} até {seasons[-1]}."
    )

    for season in seasons:
        print(f"\nTemporada {season}")

        teams = extract_teams(league_id, season)
        fixtures = extract_fixtures(league_id, season)

        player_pages = []
        if include_players:
            player_pages = extract_players(
                league_id,
                season,
                request_interval_seconds=request_interval_seconds,
                max_new_requests=max_new_player_requests_per_season,
                max_pages_per_team=max_pages_per_team,
            )

        summary.append(
            {
                "season": season,
                "teams_results": teams.get("results"),
                "fixtures_results": fixtures.get("results"),
                "player_pages": len(player_pages),
                "player_records": sum(
                    page.get("results", 0)
                    for page in player_pages
                ),
            }
        )

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extrai dados raw históricos do Brasileirão Série A."
    )
    parser.add_argument("--start-season", type=int, default=2010)
    parser.add_argument("--end-season", type=int, default=2025)
    parser.add_argument("--league", type=int, default=LEAGUE_SERIE_A)
    parser.add_argument("--interval", type=float, default=7)
    parser.add_argument(
        "--skip-players",
        action="store_true",
        help="Extrai somente equipes e partidas.",
    )
    parser.add_argument(
        "--max-new-player-requests-per-season",
        type=int,
        help="Limita N novas páginas de jogadores por temporada.",
    )
    parser.add_argument(
        "--max-new-player-requests-per-run",
        type=int,
        help=(
            "Alias antigo. Use --max-new-player-requests-per-season."
        ),
    )
    parser.add_argument(
        "--max-pages-per-team",
        type=int,
        help="Limita páginas por equipe para testes controlados.",
    )
    args = parser.parse_args()

    max_new_player_requests_per_season = (
        args.max_new_player_requests_per_season
    )

    if (
        max_new_player_requests_per_season is None
        and args.max_new_player_requests_per_run is not None
    ):
        max_new_player_requests_per_season = (
            args.max_new_player_requests_per_run
        )

    result = extract_historical_raw(
        league_id=args.league,
        start_season=args.start_season,
        end_season=args.end_season,
        include_players=not args.skip_players,
        request_interval_seconds=args.interval,
        max_new_player_requests_per_season=(
            max_new_player_requests_per_season
        ),
        max_pages_per_team=args.max_pages_per_team,
    )

    print("\nResumo:")
    for item in result:
        print(
            f"{item['season']}: "
            f"{item['teams_results']} equipes, "
            f"{item['fixtures_results']} partidas, "
            f"{item['player_pages']} páginas de jogadores, "
            f"{item['player_records']} registros de jogadores."
        )
