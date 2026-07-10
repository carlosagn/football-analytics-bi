import argparse

from sqlalchemy import text

from football_analytics.load.postgres import build_engine


WAREHOUSE_TABLES_SQL = [
    """
    CREATE TABLE warehouse.dim_date AS
    SELECT
        date_key,
        date::date AS full_date,
        year,
        month,
        month_name,
        quarter,
        day,
        day_of_week,
        day_name,
        is_weekend
    FROM stage.dates
    """,
    """
    CREATE TABLE warehouse.dim_team AS
    SELECT
        team_id,
        team_name,
        team_code,
        country,
        founded,
        is_national_team,
        team_logo_url
    FROM stage.teams
    """,
    """
    CREATE TABLE warehouse.dim_venue AS
    SELECT
        venue_id,
        venue_name,
        venue_address,
        venue_city,
        venue_capacity,
        venue_surface,
        venue_image_url
    FROM stage.venues
    """,
    """
    CREATE TABLE warehouse.dim_player AS
    SELECT
        player_id,
        player_name,
        first_name,
        last_name,
        age_at_extraction,
        birth_date::date AS birth_date,
        birth_place,
        birth_country,
        nationality,
        height_cm,
        weight_kg,
        is_injured,
        photo_url
    FROM stage.players
    """,
    """
    CREATE TABLE warehouse.bridge_team_season AS
    SELECT
        season,
        team_id,
        team_name,
        team_code,
        country,
        founded,
        is_national_team,
        team_logo_url,
        venue_id,
        venue_name,
        venue_city,
        venue_capacity
    FROM stage.team_seasons
    """,
    """
    CREATE TABLE warehouse.fact_match AS
    SELECT
        fixture_id,
        date_key,
        league_id,
        league_name,
        country,
        season,
        round,
        round_number,
        fixture_date_utc,
        fixture_timestamp,
        timezone,
        referee,
        status_long,
        status_short,
        elapsed,
        extra,
        venue_id,
        home_team_id,
        away_team_id,
        home_goals,
        away_goals,
        halftime_home_goals,
        halftime_away_goals,
        fulltime_home_goals,
        fulltime_away_goals,
        extratime_home_goals,
        extratime_away_goals,
        penalty_home_goals,
        penalty_away_goals,
        winner_team_id,
        result_label,
        is_draw,
        home_points,
        away_points,
        goal_difference,
        total_goals,
        both_teams_scored,
        over15_goals,
        over25_goals,
        over35_goals
    FROM stage.fixtures
    """,
    """
    CREATE TABLE warehouse.fact_team_match AS
    SELECT
        fixture_id,
        date_key,
        season,
        round_number,
        team_id,
        opponent_team_id,
        side,
        goals_for,
        goals_against,
        goal_difference,
        points,
        is_win,
        is_draw,
        is_loss,
        clean_sheet,
        failed_to_score
    FROM stage.fixture_team_results
    """,
    """
    CREATE TABLE warehouse.fact_player_season AS
    SELECT
        player_id,
        team_id,
        league_id,
        season,
        position,
        appearances,
        lineups,
        minutes,
        shirt_number,
        rating,
        is_captain,
        substitutes_in,
        substitutes_out,
        substitutes_bench,
        shots_total,
        shots_on,
        goals_total,
        goals_conceded,
        assists,
        saves,
        passes_total,
        passes_key,
        passes_accuracy,
        tackles_total,
        tackles_blocks,
        tackles_interceptions,
        duels_total,
        duels_won,
        dribbles_attempts,
        dribbles_success,
        dribbles_past,
        fouls_drawn,
        fouls_committed,
        yellow_cards,
        second_yellow_cards,
        red_cards,
        penalty_won,
        penalty_committed,
        penalty_scored,
        penalty_missed,
        penalty_saved,
        goal_contributions,
        minutes_per_appearance,
        goals_per90,
        assists_per90,
        goal_contributions_per90,
        shots_on_target_pct,
        duels_won_pct,
        dribbles_success_pct,
        cards_total,
        cards_per90
    FROM stage.player_season_stats
    """,
]


WAREHOUSE_CONSTRAINTS_SQL = [
    "ALTER TABLE warehouse.dim_date ADD PRIMARY KEY (date_key)",
    "ALTER TABLE warehouse.dim_team ADD PRIMARY KEY (team_id)",
    "ALTER TABLE warehouse.dim_venue ADD PRIMARY KEY (venue_id)",
    "ALTER TABLE warehouse.dim_player ADD PRIMARY KEY (player_id)",
    """
    ALTER TABLE warehouse.bridge_team_season
    ADD PRIMARY KEY (season, team_id)
    """,
    "ALTER TABLE warehouse.fact_match ADD PRIMARY KEY (fixture_id)",
    """
    ALTER TABLE warehouse.fact_team_match
    ADD PRIMARY KEY (fixture_id, team_id)
    """,
    """
    ALTER TABLE warehouse.fact_player_season
    ADD PRIMARY KEY (player_id, team_id, league_id, season)
    """,
]


WAREHOUSE_INDEXES_SQL = [
    "CREATE INDEX idx_fact_match_season ON warehouse.fact_match (season)",
    "CREATE INDEX idx_fact_match_date_key ON warehouse.fact_match (date_key)",
    """
    CREATE INDEX idx_fact_team_match_team_season
    ON warehouse.fact_team_match (team_id, season)
    """,
    """
    CREATE INDEX idx_fact_player_season_player
    ON warehouse.fact_player_season (player_id)
    """,
    """
    CREATE INDEX idx_fact_player_season_team_season
    ON warehouse.fact_player_season (team_id, season)
    """,
]


def build_warehouse(stage_schema: str = "stage", warehouse_schema: str = "warehouse"):
    if stage_schema != "stage" or warehouse_schema != "warehouse":
        raise ValueError(
            "Neste momento o script espera stage_schema='stage' "
            "e warehouse_schema='warehouse'."
        )

    engine = build_engine()

    with engine.begin() as connection:
        connection.execute(
            text(f'DROP SCHEMA IF EXISTS "{warehouse_schema}" CASCADE')
        )
        connection.execute(
            text(f'CREATE SCHEMA IF NOT EXISTS "{warehouse_schema}"')
        )

        for statement in WAREHOUSE_TABLES_SQL:
            connection.execute(text(statement))

        for statement in WAREHOUSE_CONSTRAINTS_SQL:
            connection.execute(text(statement))

        for statement in WAREHOUSE_INDEXES_SQL:
            connection.execute(text(statement))

    print("Warehouse criado com sucesso.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Constrói o schema warehouse a partir do schema stage."
    )
    parser.add_argument("--stage-schema", default="stage")
    parser.add_argument("--warehouse-schema", default="warehouse")
    args = parser.parse_args()

    build_warehouse(
        stage_schema=args.stage_schema,
        warehouse_schema=args.warehouse_schema,
    )
