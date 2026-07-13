import argparse
import time
from datetime import datetime
from pathlib import Path

from football_analytics.config.constants import LEAGUE_SERIE_A
from football_analytics.extract.api_client import ApiFootballClient
from football_analytics.extract.players import _validate_players_page
from football_analytics.load.etl_control import (
    ensure_etl_control,
    require_active_season,
)
from football_analytics.load.postgres import build_engine
from football_analytics.utils.helpers import save_json


def _validate_response(data, endpoint):
    if data.get("errors"):
        raise RuntimeError(f"Erro da API em {endpoint}: {data['errors']}")
    if not isinstance(data.get("response"), list):
        raise ValueError(f"Resposta inválida da API para {endpoint}.")


def extract_season_snapshot(
    season,
    league_id=LEAGUE_SERIE_A,
    include_players=True,
    request_interval_seconds=7,
):
    engine = build_engine()
    with engine.begin() as connection:
        ensure_etl_control(connection)
        require_active_season(connection, season)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = Path(
        f"data/raw/snapshots/{season}/snapshot_{timestamp}"
    )
    if snapshot_dir.exists():
        raise FileExistsError(f"Snapshot já existe: {snapshot_dir}")

    client = ApiFootballClient()
    request_count = 0

    teams = client.get(
        "teams", params={"league": league_id, "season": season}
    )
    request_count += 1
    _validate_response(teams, "teams")
    save_json(teams, str(snapshot_dir / "teams.json"))

    fixtures = client.get(
        "fixtures", params={"league": league_id, "season": season}
    )
    request_count += 1
    _validate_response(fixtures, "fixtures")
    save_json(fixtures, str(snapshot_dir / "fixtures.json"))

    player_pages = 0
    player_records = 0
    if include_players:
        team_ids = [
            item["team"]["id"] for item in teams["response"]
        ]
        for team_id in team_ids:
            page = 1
            total_pages = None
            while total_pages is None or page <= total_pages:
                if request_count > 0 and request_interval_seconds > 0:
                    time.sleep(request_interval_seconds)
                data = client.get(
                    "players",
                    params={
                        "league": league_id,
                        "season": season,
                        "team": team_id,
                        "page": page,
                    },
                )
                request_count += 1
                total_pages = _validate_players_page(data, team_id, page)
                save_json(
                    data,
                    str(
                        snapshot_dir
                        / "players"
                        / f"team_{team_id}"
                        / f"page_{page:03d}.json"
                    ),
                )
                player_pages += 1
                player_records += data.get("results", 0)
                page += 1

    manifest = {
        "season": season,
        "league_id": league_id,
        "extracted_at_utc": timestamp,
        "requests": request_count,
        "teams": teams.get("results", 0),
        "fixtures": fixtures.get("results", 0),
        "players_included": include_players,
        "player_pages": player_pages,
        "player_records": player_records,
    }
    save_json(manifest, str(snapshot_dir / "_SUCCESS.json"))
    print(f"Snapshot completo salvo em: {snapshot_dir.resolve()}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cria um snapshot raw imutável de uma temporada ativa."
    )
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--league", type=int, default=LEAGUE_SERIE_A)
    parser.add_argument("--interval", type=float, default=7)
    parser.add_argument("--skip-players", action="store_true")
    args = parser.parse_args()

    extract_season_snapshot(
        season=args.season,
        league_id=args.league,
        include_players=not args.skip_players,
        request_interval_seconds=args.interval,
    )
