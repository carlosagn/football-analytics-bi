from pathlib import Path

import pandas as pd

from football_analytics.utils.helpers import load_json
from football_analytics.utils.raw_snapshots import latest_complete_snapshot


def _raw_team_files(raw_dir: str = "data/raw/teams", season=None):
    raw_path = Path(raw_dir)
    if season is None:
        by_season = {
            int(path.stem): path for path in raw_path.glob("*.json")
        }
        snapshots_root = raw_path.parent / "snapshots"
        if snapshots_root.exists():
            for season_dir in snapshots_root.iterdir():
                if not season_dir.is_dir() or not season_dir.name.isdigit():
                    continue
                item = int(season_dir.name)
                snapshot = latest_complete_snapshot(raw_path, item)
                if snapshot is not None:
                    by_season[item] = snapshot / "teams.json"
        return [by_season[key] for key in sorted(by_season)]
    snapshot = latest_complete_snapshot(raw_path, season)
    if snapshot is not None:
        return [snapshot / "teams.json"]
    file = raw_path / f"{season}.json"
    return [file] if file.exists() else []


def transform_team_seasons(raw_dir: str = "data/raw/teams", season=None):
    """One row per team and season."""

    rows = []

    for file in _raw_team_files(raw_dir, season=season):
        file_season = season if season is not None else int(file.stem)
        if file.name == "teams.json":
            file_season = int(file.parent.parent.name)
        data = load_json(str(file))

        for item in data.get("response", []):
            team = item.get("team", {})
            venue = item.get("venue", {})

            rows.append(
                {
                    "Season": file_season,
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


def transform_teams(raw_dir: str = "data/raw/teams", season=None):
    """Team dimension, keeping the latest known descriptive values."""

    team_seasons = transform_team_seasons(raw_dir, season=season)

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


def transform_venues(raw_dir: str = "data/raw/teams", season=None):
    """Venue dimension from the teams endpoint."""

    rows = []

    for file in _raw_team_files(raw_dir, season=season):
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
