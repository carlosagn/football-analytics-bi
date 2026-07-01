import pandas as pd
from football_analytics.utils.helpers import load_json


def transform_teams(data: dict):

    teams = []

    for item in data["response"]:

        team = item["team"]

        teams.append({
            "TeamID": team["id"],
            "Name": team["name"],
            "Code": team["code"],
            "Founded": team["founded"],
            "LogoURL": team["logo"],
            "VenueID": item["venue"]["id"]
        })

    return pd.DataFrame(teams)

def transform_venues(data: dict):

    venues = []

    for item in data["response"]:

        venue = item["venue"]

        venues.append({
            "VenueID": venue["id"],
            "Name": venue["name"],
            "Address": venue["address"],
            "City": venue["city"],
            "Capacity": venue["capacity"],
            "Surface": venue["surface"],
            "ImageURL": venue["image"]
        })

    # Estádio pode aparecer em mais de um time, então é necessário remover duplicatas
    return pd.DataFrame(venues).drop_duplicates()

if __name__ == "__main__":

    data = load_json("data/raw/teams/2024.json")

    df_teams = transform_teams(data)
    df_venues = transform_venues(data)

    print(df_teams.head())
    print()

    print(df_venues.head())