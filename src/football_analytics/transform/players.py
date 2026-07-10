from pathlib import Path

import pandas as pd

from football_analytics.utils.helpers import load_json


def _raw_player_files(raw_dir: str = "data/raw/players"):
    return sorted(Path(raw_dir).glob("*/team_*/page_*.json"))


def _stat_value(stat, group, field):
    value = stat.get(group, {}).get(field)

    if field == "accuracy" and isinstance(value, str):
        value = value.replace("%", "")

    return value


def _height_cm(value):
    if not value or not isinstance(value, str):
        return None
    if "cm" not in value:
        return None
    return int(value.replace("cm", "").strip())


def _weight_kg(value):
    if not value or not isinstance(value, str):
        return None
    if "kg" not in value:
        return None
    return int(value.replace("kg", "").strip())


def _safe_divide(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def transform_player_season_stats(raw_dir: str = "data/raw/players"):
    """Player/team/season statistics fact table."""

    rows = []

    for file in _raw_player_files(raw_dir):
        data = load_json(str(file))

        for item in data.get("response", []):
            player = item.get("player", {})

            for stat in item.get("statistics", []):
                team = stat.get("team", {})
                league = stat.get("league", {})

                rows.append(
                    {
                        "PlayerID": player.get("id"),
                        "TeamID": team.get("id"),
                        "LeagueID": league.get("id"),
                        "Season": league.get("season"),
                        "Position": _stat_value(stat, "games", "position"),
                        "Appearances": _stat_value(
                            stat, "games", "appearences"
                        ),
                        "Lineups": _stat_value(stat, "games", "lineups"),
                        "Minutes": _stat_value(stat, "games", "minutes"),
                        "ShirtNumber": _stat_value(stat, "games", "number"),
                        "Rating": _stat_value(stat, "games", "rating"),
                        "IsCaptain": _stat_value(stat, "games", "captain"),
                        "SubstitutesIn": _stat_value(
                            stat, "substitutes", "in"
                        ),
                        "SubstitutesOut": _stat_value(
                            stat, "substitutes", "out"
                        ),
                        "SubstitutesBench": _stat_value(
                            stat, "substitutes", "bench"
                        ),
                        "ShotsTotal": _stat_value(stat, "shots", "total"),
                        "ShotsOn": _stat_value(stat, "shots", "on"),
                        "GoalsTotal": _stat_value(stat, "goals", "total"),
                        "GoalsConceded": _stat_value(
                            stat, "goals", "conceded"
                        ),
                        "Assists": _stat_value(stat, "goals", "assists"),
                        "Saves": _stat_value(stat, "goals", "saves"),
                        "PassesTotal": _stat_value(stat, "passes", "total"),
                        "PassesKey": _stat_value(stat, "passes", "key"),
                        "PassesAccuracy": _stat_value(
                            stat, "passes", "accuracy"
                        ),
                        "TacklesTotal": _stat_value(stat, "tackles", "total"),
                        "TacklesBlocks": _stat_value(
                            stat, "tackles", "blocks"
                        ),
                        "TacklesInterceptions": _stat_value(
                            stat, "tackles", "interceptions"
                        ),
                        "DuelsTotal": _stat_value(stat, "duels", "total"),
                        "DuelsWon": _stat_value(stat, "duels", "won"),
                        "DribblesAttempts": _stat_value(
                            stat, "dribbles", "attempts"
                        ),
                        "DribblesSuccess": _stat_value(
                            stat, "dribbles", "success"
                        ),
                        "DribblesPast": _stat_value(
                            stat, "dribbles", "past"
                        ),
                        "FoulsDrawn": _stat_value(stat, "fouls", "drawn"),
                        "FoulsCommitted": _stat_value(
                            stat, "fouls", "committed"
                        ),
                        "YellowCards": _stat_value(stat, "cards", "yellow"),
                        "SecondYellowCards": _stat_value(
                            stat, "cards", "yellowred"
                        ),
                        "RedCards": _stat_value(stat, "cards", "red"),
                        "PenaltyWon": _stat_value(stat, "penalty", "won"),
                        "PenaltyCommitted": _stat_value(
                            stat, "penalty", "commited"
                        ),
                        "PenaltyScored": _stat_value(
                            stat, "penalty", "scored"
                        ),
                        "PenaltyMissed": _stat_value(
                            stat, "penalty", "missed"
                        ),
                        "PenaltySaved": _stat_value(
                            stat, "penalty", "saved"
                        ),
                    }
                )

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df = df.drop_duplicates(
        subset=["PlayerID", "TeamID", "LeagueID", "Season"]
    ).reset_index(drop=True)

    numeric_columns = [
        "Appearances",
        "Lineups",
        "Minutes",
        "SubstitutesIn",
        "SubstitutesOut",
        "SubstitutesBench",
        "ShotsTotal",
        "ShotsOn",
        "GoalsTotal",
        "GoalsConceded",
        "Assists",
        "Saves",
        "PassesTotal",
        "PassesKey",
        "PassesAccuracy",
        "TacklesTotal",
        "TacklesBlocks",
        "TacklesInterceptions",
        "DuelsTotal",
        "DuelsWon",
        "DribblesAttempts",
        "DribblesSuccess",
        "DribblesPast",
        "FoulsDrawn",
        "FoulsCommitted",
        "YellowCards",
        "SecondYellowCards",
        "RedCards",
        "PenaltyWon",
        "PenaltyCommitted",
        "PenaltyScored",
        "PenaltyMissed",
        "PenaltySaved",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["GoalContributions"] = (
        df["GoalsTotal"].fillna(0) + df["Assists"].fillna(0)
    )
    df["MinutesPerAppearance"] = df.apply(
        lambda row: _safe_divide(row["Minutes"], row["Appearances"]),
        axis=1,
    )
    df["GoalsPer90"] = df.apply(
        lambda row: _safe_divide(row["GoalsTotal"] * 90, row["Minutes"]),
        axis=1,
    )
    df["AssistsPer90"] = df.apply(
        lambda row: _safe_divide(row["Assists"] * 90, row["Minutes"]),
        axis=1,
    )
    df["GoalContributionsPer90"] = df.apply(
        lambda row: _safe_divide(
            row["GoalContributions"] * 90,
            row["Minutes"],
        ),
        axis=1,
    )
    df["ShotsOnTargetPct"] = df.apply(
        lambda row: _safe_divide(row["ShotsOn"], row["ShotsTotal"]),
        axis=1,
    )
    df["DuelsWonPct"] = df.apply(
        lambda row: _safe_divide(row["DuelsWon"], row["DuelsTotal"]),
        axis=1,
    )
    df["DribblesSuccessPct"] = df.apply(
        lambda row: _safe_divide(
            row["DribblesSuccess"],
            row["DribblesAttempts"],
        ),
        axis=1,
    )
    df["CardsTotal"] = (
        df["YellowCards"].fillna(0)
        + df["SecondYellowCards"].fillna(0)
        + df["RedCards"].fillna(0)
    )
    df["CardsPer90"] = df.apply(
        lambda row: _safe_divide(row["CardsTotal"] * 90, row["Minutes"]),
        axis=1,
    )

    return df


def transform_players(raw_dir: str = "data/raw/players"):
    """Player dimension, keeping the latest known descriptive values."""

    rows = []

    for file in _raw_player_files(raw_dir):
        data = load_json(str(file))

        for item in data.get("response", []):
            player = item.get("player", {})
            birth = player.get("birth", {})

            rows.append(
                {
                    "PlayerID": player.get("id"),
                    "PlayerName": player.get("name"),
                    "FirstName": player.get("firstname"),
                    "LastName": player.get("lastname"),
                    "AgeAtExtraction": player.get("age"),
                    "BirthDate": birth.get("date"),
                    "BirthPlace": birth.get("place"),
                    "BirthCountry": birth.get("country"),
                    "Nationality": player.get("nationality"),
                    "HeightCm": _height_cm(player.get("height")),
                    "WeightKg": _weight_kg(player.get("weight")),
                    "IsInjured": player.get("injured"),
                    "PhotoURL": player.get("photo"),
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["BirthDate"] = pd.to_datetime(df["BirthDate"], errors="coerce")

    return (
        df.drop_duplicates(subset=["PlayerID"], keep="last")
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    print(transform_players().head())
    print(transform_player_season_stats().head())
