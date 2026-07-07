from football_analytics.config.constants import (
    DEFAULT_SEASON,
    LEAGUE_SERIE_A,
)
from football_analytics.extract.api_client import ApiFootballClient
from football_analytics.utils.helpers import load_json, save_json


def extract_fixtures(league_id: int, season: int):
    """Extract and persist the unmodified fixtures response for a season."""

    filepath = f"data/raw/fixtures/{season}.json"

    try:
        data = load_json(filepath)
        print(f"Partidas de {season}: arquivo raw já preservado.")
        return data
    except FileNotFoundError:
        pass

    client = ApiFootballClient()

    print("Extraindo partidas da API...")

    data = client.get(
        "fixtures",
        params={
            "league": league_id,
            "season": season,
        },
    )

    if not isinstance(data.get("response"), list):
        raise ValueError("Resposta inválida da API para partidas.")

    saved_file = save_json(
        data,
        filepath,
    )

    print(f"Arquivo salvo em: {saved_file.resolve()}")

    return data


if __name__ == "__main__":
    response = extract_fixtures(
        LEAGUE_SERIE_A,
        DEFAULT_SEASON,
    )

    print(f"{response['results']} partidas extraídas.")
