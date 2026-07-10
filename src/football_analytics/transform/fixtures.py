import re
from pathlib import Path

import pandas as pd

from football_analytics.utils.helpers import load_json


def _raw_fixture_files(raw_dir: str = "data/raw/fixtures"):
    return sorted(Path(raw_dir).glob("*.json"))


def _round_number(round_name):
    if not round_name:
        return None

    match = re.search(r"(\d+)$", round_name)
    if not match:
        return None

    return int(match.group(1))


def _points(home_goals, away_goals, status_short):
    if status_short not in {"FT", "AET", "PEN"}:
        return None, None

    if home_goals is None or away_goals is None:
        return None, None

    if home_goals > away_goals:
        return 3, 0
    if home_goals < away_goals:
        return 0, 3
    return 1, 1


def _result_label(home_goals, away_goals):
    if home_goals is None or away_goals is None:
        return None
    if home_goals > away_goals:
        return "Home Win"
    if home_goals < away_goals:
        return "Away Win"
    return "Draw"


def transform_fixtures(raw_dir: str = "data/raw/fixtures"):
    """Match fact table, one row per fixture."""

    rows = []

    for file in _raw_fixture_files(raw_dir):
        data = load_json(str(file))

        for item in data.get("response", []):
            fixture = item.get("fixture", {})
            league = item.get("league", {})
            teams = item.get("teams", {})
            goals = item.get("goals", {})
            score = item.get("score", {})
            status = fixture.get("status", {})
            venue = fixture.get("venue", {})

            home = teams.get("home", {})
            away = teams.get("away", {})

            home_goals = goals.get("home")
            away_goals = goals.get("away")
            home_points, away_points = _points(
                home_goals,
                away_goals,
                status.get("short"),
            )

            winner_team_id = None
            if home.get("winner") is True:
                winner_team_id = home.get("id")
            elif away.get("winner") is True:
                winner_team_id = away.get("id")

            total_goals = (
                home_goals + away_goals
                if home_goals is not None and away_goals is not None
                else None
            )

            rows.append(
                {
                    "FixtureID": fixture.get("id"),
                    "LeagueID": league.get("id"),
                    "LeagueName": league.get("name"),
                    "Country": league.get("country"),
                    "Season": league.get("season"),
                    "Round": league.get("round"),
                    "RoundNumber": _round_number(league.get("round")),
                    "FixtureDateUTC": fixture.get("date"),
                    "FixtureTimestamp": fixture.get("timestamp"),
                    "Timezone": fixture.get("timezone"),
                    "Referee": fixture.get("referee"),
                    "StatusLong": status.get("long"),
                    "StatusShort": status.get("short"),
                    "Elapsed": status.get("elapsed"),
                    "Extra": status.get("extra"),
                    "VenueID": venue.get("id"),
                    "VenueName": venue.get("name"),
                    "VenueCity": venue.get("city"),
                    "HomeTeamID": home.get("id"),
                    "HomeTeamName": home.get("name"),
                    "AwayTeamID": away.get("id"),
                    "AwayTeamName": away.get("name"),
                    "HomeGoals": home_goals,
                    "AwayGoals": away_goals,
                    "HalftimeHomeGoals": score.get("halftime", {}).get("home"),
                    "HalftimeAwayGoals": score.get("halftime", {}).get("away"),
                    "FulltimeHomeGoals": score.get("fulltime", {}).get("home"),
                    "FulltimeAwayGoals": score.get("fulltime", {}).get("away"),
                    "ExtratimeHomeGoals": score.get("extratime", {}).get("home"),
                    "ExtratimeAwayGoals": score.get("extratime", {}).get("away"),
                    "PenaltyHomeGoals": score.get("penalty", {}).get("home"),
                    "PenaltyAwayGoals": score.get("penalty", {}).get("away"),
                    "WinnerTeamID": winner_team_id,
                    "ResultLabel": _result_label(home_goals, away_goals),
                    "IsDraw": home.get("winner") is False
                    and away.get("winner") is False,
                    "HomePoints": home_points,
                    "AwayPoints": away_points,
                    "GoalDifference": (
                        home_goals - away_goals
                        if home_goals is not None and away_goals is not None
                        else None
                    ),
                    "TotalGoals": total_goals,
                    "BothTeamsScored": (
                        home_goals > 0 and away_goals > 0
                        if home_goals is not None and away_goals is not None
                        else None
                    ),
                    "Over15Goals": (
                        total_goals > 1.5 if total_goals is not None else None
                    ),
                    "Over25Goals": (
                        total_goals > 2.5 if total_goals is not None else None
                    ),
                    "Over35Goals": (
                        total_goals > 3.5 if total_goals is not None else None
                    ),
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["FixtureDateUTC"] = pd.to_datetime(
        df["FixtureDateUTC"],
        errors="coerce",
        utc=True,
    )
    df["FixtureDate"] = df["FixtureDateUTC"].dt.date
    df["DateKey"] = df["FixtureDateUTC"].dt.strftime("%Y%m%d")

    return df.drop_duplicates(subset=["FixtureID"]).reset_index(drop=True)


def transform_fixture_team_results(raw_dir: str = "data/raw/fixtures"):
    """One row per team in each fixture, useful for standings-like analysis."""

    fixtures = transform_fixtures(raw_dir)
    rows = []

    for item in fixtures.to_dict("records"):
        sides = [
            (
                "Home",
                item["HomeTeamID"],
                item["AwayTeamID"],
                item["HomeGoals"],
                item["AwayGoals"],
                item["HomePoints"],
            ),
            (
                "Away",
                item["AwayTeamID"],
                item["HomeTeamID"],
                item["AwayGoals"],
                item["HomeGoals"],
                item["AwayPoints"],
            ),
        ]

        for side, team_id, opponent_id, goals_for, goals_against, points in sides:
            rows.append(
                {
                    "FixtureID": item["FixtureID"],
                    "DateKey": item["DateKey"],
                    "Season": item["Season"],
                    "RoundNumber": item["RoundNumber"],
                    "TeamID": team_id,
                    "OpponentTeamID": opponent_id,
                    "Side": side,
                    "GoalsFor": goals_for,
                    "GoalsAgainst": goals_against,
                    "GoalDifference": (
                        goals_for - goals_against
                        if goals_for is not None and goals_against is not None
                        else None
                    ),
                    "Points": points,
                    "IsWin": points == 3,
                    "IsDraw": points == 1,
                    "IsLoss": points == 0,
                    "CleanSheet": goals_against == 0
                    if goals_against is not None
                    else None,
                    "FailedToScore": goals_for == 0
                    if goals_for is not None
                    else None,
                }
            )

    return pd.DataFrame(rows)


def transform_dates(raw_dir: str = "data/raw/fixtures"):
    fixtures = transform_fixtures(raw_dir)

    if fixtures.empty:
        return pd.DataFrame()

    dates = pd.DataFrame(
        {
            "Date": pd.to_datetime(fixtures["FixtureDate"]),
        }
    ).drop_duplicates()

    dates["DateKey"] = dates["Date"].dt.strftime("%Y%m%d")
    dates["Year"] = dates["Date"].dt.year
    dates["Month"] = dates["Date"].dt.month
    dates["MonthName"] = dates["Date"].dt.month_name()
    dates["Quarter"] = dates["Date"].dt.quarter
    dates["Day"] = dates["Date"].dt.day
    dates["DayOfWeek"] = dates["Date"].dt.dayofweek + 1
    dates["DayName"] = dates["Date"].dt.day_name()
    dates["IsWeekend"] = dates["DayOfWeek"].isin([6, 7])

    return dates.sort_values("DateKey").reset_index(drop=True)


if __name__ == "__main__":
    print(transform_fixtures().head())
    print(transform_fixture_team_results().head())
    print(transform_dates().head())
