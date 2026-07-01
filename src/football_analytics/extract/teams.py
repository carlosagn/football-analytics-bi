from football_analytics.config.constants import (
    DEFAULT_SEASON,
    LEAGUE_SERIE_A
)

from football_analytics.extract.api_client import ApiFootballClient
from football_analytics.utils.helpers import save_json

def extract_teams(
    league_id: int,
    season: int
):

    client = ApiFootballClient()

    data = client.get(
        "teams",
        params={
            "league": league_id,
            "season": season
        }
    )

    save_json(
        data,
        f"data/raw/teams_{season}.json"
    )

    return data


if __name__ == "__main__":

    response = extract_teams(
        LEAGUE_SERIE_A,
        DEFAULT_SEASON
    )

    print(f"{response['results']} equipes extraídas.")