import argparse

from sqlalchemy import text

from football_analytics.load.etl_control import (
    ensure_etl_control,
    finish_run,
    require_active_season,
    start_run,
)
from football_analytics.load.postgres import build_engine


UPSERT_DIMENSIONS_SQL = [
    """
    INSERT INTO warehouse.dim_date
    SELECT
        d.date_key,
        d.date::date,
        d.year,
        d.month,
        d.month_name,
        d.quarter,
        d.day,
        d.day_of_week,
        d.day_name,
        d.is_weekend
    FROM stage.dates d
    WHERE d.date_key IN (
        SELECT date_key FROM stage.fixtures WHERE season = :season
    )
    ON CONFLICT (date_key) DO UPDATE SET
        full_date = EXCLUDED.full_date,
        year = EXCLUDED.year,
        month = EXCLUDED.month,
        month_name = EXCLUDED.month_name,
        quarter = EXCLUDED.quarter,
        day = EXCLUDED.day,
        day_of_week = EXCLUDED.day_of_week,
        day_name = EXCLUDED.day_name,
        is_weekend = EXCLUDED.is_weekend
    """,
    """
    INSERT INTO warehouse.dim_team
    SELECT
        t.team_id,
        t.team_name,
        t.team_code,
        t.founded,
        t.team_logo_url
    FROM stage.teams t
    WHERE t.team_id IN (
        SELECT team_id FROM stage.team_seasons WHERE season = :season
    )
    ON CONFLICT (team_id) DO UPDATE SET
        team_name = EXCLUDED.team_name,
        team_code = EXCLUDED.team_code,
        founded = EXCLUDED.founded,
        team_logo_url = EXCLUDED.team_logo_url
    """,
    """
    INSERT INTO warehouse.dim_player
    SELECT
        p.player_id,
        p.player_name,
        p.first_name,
        p.last_name,
        p.birth_date::date,
        p.birth_place,
        p.birth_country,
        p.nationality,
        p.height_cm,
        p.weight_kg,
        p.photo_url
    FROM stage.players p
    WHERE p.player_id IN (
        SELECT player_id
        FROM stage.player_season_stats
        WHERE season = :season
    )
    ON CONFLICT (player_id) DO UPDATE SET
        player_name = EXCLUDED.player_name,
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        birth_date = EXCLUDED.birth_date,
        birth_place = EXCLUDED.birth_place,
        birth_country = EXCLUDED.birth_country,
        nationality = EXCLUDED.nationality,
        height_cm = EXCLUDED.height_cm,
        weight_kg = EXCLUDED.weight_kg,
        photo_url = EXCLUDED.photo_url
    """,
    """
    INSERT INTO warehouse.dim_season
    SELECT
        f.season,
        'Brasileirão ' || f.season::text,
        MIN(f.fixture_date_utc::date),
        MAX(f.fixture_date_utc::date),
        COUNT(*),
        (
            SELECT COUNT(DISTINCT ts.team_id)
            FROM stage.team_seasons ts
            WHERE ts.season = :season
        ),
        BOOL_AND(f.status_short IN ('FT', 'AET', 'PEN', 'CANC'))
    FROM stage.fixtures f
    WHERE f.season = :season
    GROUP BY f.season
    ON CONFLICT (season_key) DO UPDATE SET
        season_name = EXCLUDED.season_name,
        start_date = EXCLUDED.start_date,
        end_date = EXCLUDED.end_date,
        number_of_matches = EXCLUDED.number_of_matches,
        number_of_teams = EXCLUDED.number_of_teams,
        is_completed = EXCLUDED.is_completed
    """,
    """
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
            venue_id::bigint,
            venue_name,
            NULL::text,
            venue_city,
            NULL::bigint,
            NULL::text,
            2
        FROM stage.fixtures
        WHERE venue_id IS NOT NULL
    ),
    remapped AS (
        SELECT
            COALESCE(c.canonical_venue_id, v.venue_id) AS venue_id,
            v.venue_name,
            v.venue_address,
            v.venue_city,
            v.venue_capacity,
            v.venue_image_url,
            v.source_priority,
            CASE WHEN v.venue_id = COALESCE(c.canonical_venue_id, v.venue_id)
                THEN 0 ELSE 1 END AS mapping_priority
        FROM venue_sources v
        LEFT JOIN manual.venue_corrections c
            ON c.source_venue_id = v.venue_id
    ),
    base AS (
        SELECT DISTINCT ON (venue_id)
            venue_id, venue_name, venue_address, venue_city,
            venue_capacity, venue_image_url
        FROM remapped
        ORDER BY venue_id, mapping_priority, source_priority
    ),
    corrected AS (
        SELECT
            COALESCE(b.venue_id, c.canonical_venue_id) AS venue_id,
            COALESCE(c.venue_name, b.venue_name) AS venue_name,
            COALESCE(c.venue_address, b.venue_address) AS venue_address,
            COALESCE(c.venue_city, b.venue_city) AS venue_city,
            COALESCE(c.venue_capacity, b.venue_capacity) AS venue_capacity,
            COALESCE(c.venue_image_url, b.venue_image_url) AS venue_image_url
        FROM base b
        FULL OUTER JOIN manual.venue_corrections c
            ON c.source_venue_id = c.canonical_venue_id
           AND c.canonical_venue_id = b.venue_id
        WHERE c.source_venue_id IS NULL
           OR c.source_venue_id = c.canonical_venue_id
    )
    INSERT INTO warehouse.dim_venue
    SELECT * FROM corrected
    ON CONFLICT (venue_id) DO UPDATE SET
        venue_name = EXCLUDED.venue_name,
        venue_address = EXCLUDED.venue_address,
        venue_city = EXCLUDED.venue_city,
        venue_capacity = EXCLUDED.venue_capacity,
        venue_image_url = EXCLUDED.venue_image_url
    """,
]


DELETE_SEASON_SQL = [
    "DELETE FROM warehouse.fact_team_match WHERE season_key = :season",
    "DELETE FROM warehouse.fact_player_season WHERE season_key = :season",
    "DELETE FROM warehouse.fact_match WHERE season_key = :season",
    "DELETE FROM warehouse.bridge_team_season WHERE season_key = :season",
]


INSERT_SEASON_SQL = [
    """
    INSERT INTO warehouse.bridge_team_season
    SELECT
        ts.season,
        ts.team_id,
        ts.team_name,
        ts.team_code,
        ts.founded,
        ts.team_logo_url,
        COALESCE(vc.canonical_venue_id, ts.venue_id::bigint),
        ts.venue_name,
        ts.venue_city,
        ts.venue_capacity
    FROM stage.team_seasons ts
    LEFT JOIN manual.venue_corrections vc
        ON vc.source_venue_id = ts.venue_id::bigint
    WHERE ts.season = :season
    """,
    """
    INSERT INTO warehouse.fact_match
    SELECT
        f.fixture_id,
        f.date_key,
        f.season,
        f.round,
        f.round_number,
        f.fixture_date_utc,
        f.fixture_timestamp,
        f.timezone,
        f.referee,
        f.status_short,
        f.elapsed,
        f.extra,
        COALESCE(vc.canonical_venue_id, f.venue_id::bigint),
        f.home_team_id,
        f.away_team_id,
        f.home_goals,
        f.away_goals,
        f.halftime_home_goals,
        f.halftime_away_goals,
        f.fulltime_home_goals,
        f.fulltime_away_goals,
        f.extratime_home_goals,
        f.extratime_away_goals,
        f.penalty_home_goals,
        f.penalty_away_goals,
        f.winner_team_id::bigint,
        f.result_label,
        f.is_draw,
        f.home_points,
        f.away_points,
        f.goal_difference,
        f.total_goals,
        f.both_teams_scored,
        f.over15_goals,
        f.over25_goals,
        f.over35_goals
    FROM stage.fixtures f
    LEFT JOIN manual.venue_corrections vc
        ON vc.source_venue_id = f.venue_id::bigint
    WHERE f.season = :season
    """,
    """
    INSERT INTO warehouse.fact_team_match
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
    WHERE season = :season
    """,
    """
    INSERT INTO warehouse.fact_player_season
    SELECT
        player_id,
        team_id,
        season,
        CASE position
            WHEN 'Goalkeeper' THEN 'GK'
            WHEN 'Defender' THEN 'DF'
            WHEN 'Midfielder' THEN 'MF'
            WHEN 'Attacker' THEN 'FW'
            WHEN 'Forward' THEN 'FW'
        END,
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
    WHERE season = :season
    """,
]


def _validate_stage(connection, season):
    counts = {}
    for table_name in (
        "team_seasons",
        "fixtures",
        "fixture_team_results",
        "player_season_stats",
    ):
        counts[table_name] = connection.execute(
            text(
                f"SELECT COUNT(*) FROM stage.{table_name} "
                "WHERE season = :season"
            ),
            {"season": season},
        ).scalar()
        if counts[table_name] == 0:
            raise ValueError(
                f"stage.{table_name} não possui dados para {season}."
            )

    if counts["fixture_team_results"] != counts["fixtures"] * 2:
        raise ValueError(
            "Cada partida deve possuir exatamente dois resultados por equipe."
        )

    unknown_positions = connection.execute(
        text(
            """
            SELECT DISTINCT position
            FROM stage.player_season_stats
            WHERE season = :season
              AND position NOT IN (
                  'Goalkeeper', 'Defender', 'Midfielder',
                  'Attacker', 'Forward'
              )
            """
        ),
        {"season": season},
    ).fetchall()
    if unknown_positions:
        raise ValueError(f"Posições desconhecidas: {unknown_positions}")

    return counts


def refresh_warehouse_season(season, force=False):
    engine = build_engine()
    run_id = None

    try:
        with engine.begin() as connection:
            ensure_etl_control(connection)
            require_active_season(connection, season, force=force)
            run_id = start_run(connection, season, "warehouse_incremental")

        with engine.begin() as connection:
            counts = _validate_stage(connection, season)

            for statement in UPSERT_DIMENSIONS_SQL:
                connection.execute(text(statement), {"season": season})
            for statement in DELETE_SEASON_SQL:
                connection.execute(text(statement), {"season": season})
            for statement in INSERT_SEASON_SQL:
                connection.execute(text(statement), {"season": season})

            connection.execute(
                text(
                    """
                    UPDATE etl.season_control
                    SET last_successful_run_at = CURRENT_TIMESTAMP
                    WHERE season = :season
                    """
                ),
                {"season": season},
            )

        finish_run(engine, run_id, "success", row_counts=counts)
        print(f"Warehouse atualizado somente para a temporada {season}.")
        return counts
    except Exception as exc:
        if run_id is not None:
            finish_run(engine, run_id, "failed", error_message=str(exc))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Atualiza somente uma temporada no warehouse."
    )
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    refresh_warehouse_season(args.season, force=args.force)
