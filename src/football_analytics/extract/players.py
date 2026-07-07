import argparse
import time
from pathlib import Path

from football_analytics.config.constants import (
    DEFAULT_SEASON,
    LEAGUE_SERIE_A,
)
from football_analytics.extract.api_client import ApiFootballClient
from football_analytics.utils.helpers import load_json, save_json


def _load_team_ids(season: int):
    teams_file = Path(f"data/raw/teams/{season}.json")

    if not teams_file.exists():
        raise FileNotFoundError(
            f"Extraia as equipes antes dos jogadores: {teams_file}"
        )

    teams_data = load_json(str(teams_file))
    team_ids = [
        item["team"]["id"]
        for item in teams_data.get("response", [])
    ]

    if not team_ids:
        raise ValueError(
            f"Nenhuma equipe encontrada no arquivo {teams_file}."
        )

    return team_ids


def _validate_players_page(data: dict, team_id: int, page: int):
    errors = data.get("errors")
    if errors:
        raise RuntimeError(
            f"A API retornou erro para a equipe {team_id}, "
            f"página {page}: {errors}"
        )

    if not isinstance(data.get("response"), list):
        raise ValueError(
            f"Resposta inválida para a equipe {team_id}, página {page}."
        )

    paging = data.get("paging")
    if not isinstance(paging, dict):
        raise ValueError(
            f"Paginação inválida para a equipe {team_id}, página {page}."
        )

    total_pages = paging.get("total")
    if not isinstance(total_pages, int) or total_pages < page:
        raise ValueError(
            f"Total de páginas inválido para a equipe {team_id}: "
            f"{total_pages!r}."
        )

    return total_pages


def extract_players(
    league_id: int,
    season: int,
    request_interval_seconds: float = 7,
    max_new_requests=None,
    max_pages_per_team=None,
):
    """Extract unmodified player pages, partitioned by team.

    Existing files are preserved. By default there is no artificial page cap,
    so paid API keys can continue beyond page 3. Use max_pages_per_team only
    for controlled tests or temporary limits.
    """

    client = ApiFootballClient()
    team_ids = _load_team_ids(season)
    pages = []
    limited_teams = []
    new_requests = 0

    print(f"Extraindo jogadores de {len(team_ids)} equipes...")

    for team_index, team_id in enumerate(team_ids, start=1):
        current_page = 1
        total_pages = None

        while total_pages is None or current_page <= total_pages:
            filepath = Path(
                f"data/raw/players/{season}/team_{team_id}/"
                f"page_{current_page:03d}.json"
            )

            if filepath.exists():
                data = load_json(str(filepath))
                print(
                    f"Equipe {team_index}/{len(team_ids)}, "
                    f"página {current_page}: arquivo já preservado."
                )
            else:
                if pages and request_interval_seconds > 0:
                    time.sleep(request_interval_seconds)

                data = client.get(
                    "players",
                    params={
                        "league": league_id,
                        "season": season,
                        "team": team_id,
                        "page": current_page,
                    },
                )
                new_requests += 1

            page_total = _validate_players_page(
                data,
                team_id,
                current_page,
            )

            if total_pages is None:
                total_pages = page_total
                if (
                    max_pages_per_team is not None
                    and total_pages > max_pages_per_team
                ):
                    limited_teams.append((team_id, total_pages))
            elif page_total != total_pages:
                raise ValueError(
                    f"O total de páginas da equipe {team_id} mudou "
                    f"de {total_pages} para {page_total}."
                )

            if not filepath.exists():
                saved_file = save_json(data, str(filepath))
                print(
                    f"Equipe {team_index}/{len(team_ids)}, "
                    f"página {current_page}/{total_pages} salva em: "
                    f"{saved_file.resolve()}"
                )

            pages.append(data)
            current_page += 1

            if (
                max_new_requests is not None
                and new_requests >= max_new_requests
            ):
                print(
                    f"Lote encerrado após {new_requests} novas requisições."
                )
                return pages

            if (
                max_pages_per_team is not None
                and current_page > max_pages_per_team
            ):
                break

    if limited_teams:
        details = ", ".join(
            f"{team_id} ({total_pages} páginas)"
            for team_id, total_pages in limited_teams
        )
        print(
            "AVISO: a extração foi limitada por max_pages_per_team. "
            f"Equipes com extração parcial: {details}."
        )

    return pages


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extrai jogadores brutos por equipe e temporada."
    )
    parser.add_argument("--season", type=int, default=DEFAULT_SEASON)
    parser.add_argument("--league", type=int, default=LEAGUE_SERIE_A)
    parser.add_argument("--interval", type=float, default=7)
    parser.add_argument("--max-new-requests", type=int)
    parser.add_argument("--max-pages-per-team", type=int)
    args = parser.parse_args()

    responses = extract_players(
        args.league,
        args.season,
        request_interval_seconds=args.interval,
        max_new_requests=args.max_new_requests,
        max_pages_per_team=args.max_pages_per_team,
    )

    total_records = sum(page["results"] for page in responses)
    print(f"{total_records} registros de jogadores extraídos.")
