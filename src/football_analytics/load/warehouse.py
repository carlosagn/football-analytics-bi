import argparse

from sqlalchemy import text

from football_analytics.load.postgres import build_engine


MANUAL_REFERENCE_SQL = [
    "CREATE SCHEMA IF NOT EXISTS manual",
    """
    CREATE TABLE IF NOT EXISTS manual.venue_corrections (
        source_venue_id BIGINT PRIMARY KEY,
        canonical_venue_id BIGINT NOT NULL,
        venue_name TEXT,
        venue_address TEXT,
        venue_city TEXT,
        venue_capacity BIGINT,
        venue_image_url TEXT,
        correction_reason TEXT,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


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
        founded,
        team_logo_url
    FROM stage.teams
    """,
    """
    CREATE TABLE warehouse.dim_venue AS
    WITH venue_sources AS (
        SELECT
            venue_id::bigint AS venue_id,
            venue_name,
            venue_address,
            venue_city,
            venue_capacity::bigint AS venue_capacity,
            venue_image_url,
            1 AS source_priority
        FROM stage.venues
        UNION ALL
        SELECT DISTINCT
            venue_id::bigint AS venue_id,
            venue_name,
            NULL::text AS venue_address,
            venue_city,
            NULL::bigint AS venue_capacity,
            NULL::text AS venue_image_url,
            2 AS source_priority
        FROM stage.fixtures
        WHERE venue_id IS NOT NULL
    ),
    remapped_sources AS (
        SELECT
            COALESCE(c.canonical_venue_id, v.venue_id) AS venue_id,
            v.venue_name,
            v.venue_address,
            v.venue_city,
            v.venue_capacity,
            v.venue_image_url,
            v.source_priority,
            CASE
                WHEN v.venue_id = COALESCE(c.canonical_venue_id, v.venue_id)
                    THEN 0
                ELSE 1
            END AS mapping_priority
        FROM venue_sources v
        LEFT JOIN manual.venue_corrections c
            ON c.source_venue_id = v.venue_id
    ),
    canonical_base AS (
        SELECT DISTINCT ON (venue_id)
            venue_id,
            venue_name,
            venue_address,
            venue_city,
            venue_capacity,
            venue_image_url
        FROM remapped_sources
        ORDER BY venue_id, mapping_priority, source_priority
    ),
    direct_corrections AS (
        SELECT *
        FROM manual.venue_corrections
        WHERE source_venue_id = canonical_venue_id
    )
    SELECT
        COALESCE(b.venue_id, c.canonical_venue_id) AS venue_id,
        COALESCE(c.venue_name, b.venue_name) AS venue_name,
        COALESCE(c.venue_address, b.venue_address) AS venue_address,
        COALESCE(c.venue_city, b.venue_city) AS venue_city,
        COALESCE(c.venue_capacity, b.venue_capacity) AS venue_capacity,
        COALESCE(c.venue_image_url, b.venue_image_url) AS venue_image_url
    FROM canonical_base b
    FULL OUTER JOIN direct_corrections c
        ON c.canonical_venue_id = b.venue_id
    """,
    """
    CREATE TABLE warehouse.dim_player AS
    SELECT
        player_id,
        player_name,
        first_name,
        last_name,
        birth_date::date AS birth_date,
        birth_place,
        birth_country,
        nationality,
        height_cm,
        weight_kg,
        photo_url
    FROM stage.players
    """,
    """
    CREATE TABLE warehouse.dim_season AS
    WITH fixture_summary AS (
        SELECT
            season,
            MIN(fixture_date_utc::date) AS start_date,
            MAX(fixture_date_utc::date) AS end_date,
            COUNT(*) AS number_of_matches,
            BOOL_AND(status_short IN ('FT', 'AET', 'PEN', 'CANC'))
                AS is_completed
        FROM stage.fixtures
        GROUP BY season
    ),
    team_summary AS (
        SELECT season, COUNT(DISTINCT team_id) AS number_of_teams
        FROM stage.team_seasons
        GROUP BY season
    )
    SELECT
        f.season AS season_key,
        'Brasileirão ' || f.season::text AS season_name,
        f.start_date,
        f.end_date,
        f.number_of_matches,
        t.number_of_teams,
        f.is_completed
    FROM fixture_summary f
    LEFT JOIN team_summary t ON t.season = f.season
    """,
    """
    CREATE TABLE warehouse.dim_position (
        position_key VARCHAR(2) PRIMARY KEY,
        position_name VARCHAR(30) NOT NULL,
        position_group VARCHAR(30) NOT NULL,
        sort_order SMALLINT NOT NULL UNIQUE
    )
    """,
    """
    INSERT INTO warehouse.dim_position
        (position_key, position_name, position_group, sort_order)
    VALUES
        ('GK', 'Goalkeeper', 'Goleiro', 1),
        ('DF', 'Defender', 'Defesa', 2),
        ('MF', 'Midfielder', 'Meio-campo', 3),
        ('FW', 'Forward', 'Ataque', 4)
    """,
    """
    CREATE TABLE warehouse.bridge_team_season AS
    SELECT
        ts.season AS season_key,
        ts.team_id,
        ts.team_name,
        ts.team_code,
        ts.founded,
        ts.team_logo_url,
        COALESCE(vc.canonical_venue_id, ts.venue_id::bigint) AS venue_id,
        ts.venue_name,
        ts.venue_city,
        ts.venue_capacity
    FROM stage.team_seasons ts
    LEFT JOIN manual.venue_corrections vc
        ON vc.source_venue_id = ts.venue_id::bigint
    """,
    """
    CREATE TABLE warehouse.fact_match AS
    SELECT
        fixture_id,
        date_key,
        season AS season_key,
        round,
        round_number,
        fixture_date_utc,
        fixture_timestamp,
        timezone,
        referee,
        status_short,
        elapsed,
        extra,
        COALESCE(vc.canonical_venue_id, f.venue_id::bigint) AS venue_id,
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
        winner_team_id::bigint AS winner_team_id,
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
    FROM stage.fixtures f
    LEFT JOIN manual.venue_corrections vc
        ON vc.source_venue_id = f.venue_id::bigint
    """,
    """
    CREATE TABLE warehouse.fact_team_match AS
    SELECT
        fixture_id,
        date_key,
        season AS season_key,
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
        season AS season_key,
        CASE position
            WHEN 'Goalkeeper' THEN 'GK'
            WHEN 'Defender' THEN 'DF'
            WHEN 'Midfielder' THEN 'MF'
            WHEN 'Attacker' THEN 'FW'
            WHEN 'Forward' THEN 'FW'
        END AS position_key,
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
    "ALTER TABLE warehouse.dim_season ADD PRIMARY KEY (season_key)",
    """
    ALTER TABLE warehouse.bridge_team_season
    ADD PRIMARY KEY (season_key, team_id)
    """,
    "ALTER TABLE warehouse.fact_match ADD PRIMARY KEY (fixture_id)",
    """
    ALTER TABLE warehouse.fact_team_match
    ADD PRIMARY KEY (fixture_id, team_id)
    """,
    """
    ALTER TABLE warehouse.fact_player_season
    ADD PRIMARY KEY (player_id, team_id, season_key)
    """,
    """
    ALTER TABLE warehouse.bridge_team_season
    ADD FOREIGN KEY (season_key) REFERENCES warehouse.dim_season (season_key),
    ADD FOREIGN KEY (team_id) REFERENCES warehouse.dim_team (team_id)
    """,
    """
    ALTER TABLE warehouse.fact_match
    ADD FOREIGN KEY (date_key) REFERENCES warehouse.dim_date (date_key),
    ADD FOREIGN KEY (season_key) REFERENCES warehouse.dim_season (season_key),
    ADD FOREIGN KEY (venue_id) REFERENCES warehouse.dim_venue (venue_id),
    ADD FOREIGN KEY (home_team_id) REFERENCES warehouse.dim_team (team_id),
    ADD FOREIGN KEY (away_team_id) REFERENCES warehouse.dim_team (team_id),
    ADD FOREIGN KEY (winner_team_id) REFERENCES warehouse.dim_team (team_id)
    """,
    """
    ALTER TABLE warehouse.fact_team_match
    ADD FOREIGN KEY (fixture_id) REFERENCES warehouse.fact_match (fixture_id),
    ADD FOREIGN KEY (date_key) REFERENCES warehouse.dim_date (date_key),
    ADD FOREIGN KEY (season_key) REFERENCES warehouse.dim_season (season_key),
    ADD FOREIGN KEY (team_id) REFERENCES warehouse.dim_team (team_id),
    ADD FOREIGN KEY (opponent_team_id) REFERENCES warehouse.dim_team (team_id)
    """,
    """
    ALTER TABLE warehouse.fact_player_season
    ADD FOREIGN KEY (player_id) REFERENCES warehouse.dim_player (player_id),
    ADD FOREIGN KEY (team_id) REFERENCES warehouse.dim_team (team_id),
    ADD FOREIGN KEY (season_key) REFERENCES warehouse.dim_season (season_key),
    ADD FOREIGN KEY (position_key)
        REFERENCES warehouse.dim_position (position_key)
    """,
]


WAREHOUSE_INDEXES_SQL = [
    "CREATE INDEX idx_fact_match_season ON warehouse.fact_match (season_key)",
    "CREATE INDEX idx_fact_match_date_key ON warehouse.fact_match (date_key)",
    """
    CREATE INDEX idx_fact_team_match_team_season
    ON warehouse.fact_team_match (team_id, season_key)
    """,
    """
    CREATE INDEX idx_fact_player_season_player
    ON warehouse.fact_player_season (player_id)
    """,
    """
    CREATE INDEX idx_fact_player_season_team_season
    ON warehouse.fact_player_season (team_id, season_key)
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
        for statement in MANUAL_REFERENCE_SQL:
            connection.execute(text(statement))

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
