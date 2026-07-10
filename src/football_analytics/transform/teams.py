from pathlib import Path

import pandas as pd

from football_analytics.utils.helpers import load_json


def _raw_team_files(raw_dir: str = "data/raw/teams"):
    return sorted(Path(raw_dir).glob("*.json"))


def transform_team_seasons(raw_dir: str = "data/raw/teams"):
    """One row per team and season."""

    rows = []

    for file in _raw_team_files(raw_dir):
        season = int(file.stem)
        data = load_json(str(file))

        for item in data.get("response", []):
            team = item.get("team", {})
            venue = item.get("venue", {})

            rows.append(
                {
                    "Season": season,
                    "TeamID": team.get("id"),
                    "TeamName": team.get("name"),
                    "TeamCode": team.get("code"),
                    "Country": team.get("country"),
                    "Founded": team.get("founded"),
                    "IsNationalTeam": team.get("national"),
                    "TeamLogoURL": team.get("logo"),
                    "VenueID": venue.get("id"),
                    "VenueName": venue.get("name"),
                    "VenueCity": venue.get("city"),
                    "VenueCapacity": venue.get("capacity"),
                }
            )

    return pd.DataFrame(rows).drop_duplicates(
        subset=["Season", "TeamID"]
    )


def transform_teams(raw_dir: str = "data/raw/teams"):
    """Team dimension, keeping the latest known descriptive values."""

    team_seasons = transform_team_seasons(raw_dir)

    if team_seasons.empty:
        return team_seasons

    columns = [
        "TeamID",
        "TeamName",
        "TeamCode",
        "Country",
        "Founded",
        "IsNationalTeam",
        "TeamLogoURL",
    ]

    return (
        team_seasons.sort_values(["TeamID", "Season"])
        .drop_duplicates(subset=["TeamID"], keep="last")[columns]
        .reset_index(drop=True)
    )


def transform_venues(raw_dir: str = "data/raw/teams"):
    """Venue dimension from the teams endpoint."""

    rows = []

    for file in _raw_team_files(raw_dir):
        data = load_json(str(file))

        for item in data.get("response", []):
            venue = item.get("venue", {})

            rows.append(
                {
                    "VenueID": venue.get("id"),
                    "VenueName": venue.get("name"),
                    "VenueAddress": venue.get("address"),
                    "VenueCity": venue.get("city"),
                    "VenueCapacity": venue.get("capacity"),
                    "VenueSurface": venue.get("surface"),
                    "VenueImageURL": venue.get("image"),
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    return (
        df.dropna(subset=["VenueID"])
        .drop_duplicates(subset=["VenueID"], keep="last")
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    print(transform_teams().head())
    print(transform_team_seasons().head())
    print(transform_venues().head())
