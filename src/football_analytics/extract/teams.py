from football_analytics.config.constants import (
    DEFAULT_SEASON,
    LEAGUE_SERIE_A
)

from football_analytics.extract.api_client import ApiFootballClient
from football_analytics.utils.helpers import load_json, save_json

def extract_teams(league_id: int, season: int):
    filepath = f"data/raw/teams/{season}.json"

    try:
        data = load_json(filepath)
        print(f"Equipes de {season}: arquivo raw já preservado.")
        return data
    except FileNotFoundError:
        pass

    client = ApiFootballClient()

    print("Extraindo equipes da API...")

    data = client.get(
        "teams",
        params={
            "league": league_id,
            "season": season
        }
    )

    print("Salvando arquivo JSON...")

    saved_file = save_json(
        data,
        filepath
    )

    print(f"Arquivo salvo em: {saved_file.resolve()}")

    return data


if __name__ == "__main__":

    response = extract_teams(
        LEAGUE_SERIE_A,
        DEFAULT_SEASON
    )

    print(f"{response['results']} equipes extraídas.")
