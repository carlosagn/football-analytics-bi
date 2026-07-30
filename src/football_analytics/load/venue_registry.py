import csv
from pathlib import Path

from sqlalchemy import text


REFERENCE_DIR = Path(__file__).resolve().parents[3] / "reference"


REGISTRY_SQL = [
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
    """
    CREATE TABLE IF NOT EXISTS manual.venue_registry (
        venue_key BIGSERIAL PRIMARY KEY,
        api_venue_id BIGINT,
        venue_name TEXT NOT NULL UNIQUE,
        venue_address TEXT,
        venue_city TEXT,
        venue_capacity BIGINT,
        venue_image_url TEXT,
        review_status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    ALTER TABLE manual.venue_registry
    ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'pending'
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_venue_registry_api_id
    ON manual.venue_registry (api_venue_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS manual.venue_name_alias (
        venue_name_raw TEXT PRIMARY KEY,
        venue_key BIGINT NOT NULL REFERENCES manual.venue_registry (venue_key),
        review_status TEXT NOT NULL DEFAULT 'pending',
        match_reason TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    ALTER TABLE manual.venue_name_alias
    ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'pending'
    """,
    """
    ALTER TABLE manual.venue_name_alias
    ADD COLUMN IF NOT EXISTS match_reason TEXT
    """,
]


def _read_reference(filename):
    path = REFERENCE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de referência não encontrado: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def _optional_int(value):
    return int(value) if value else None


def _warehouse_venue_columns(connection):
    return {
        row[0]
        for row in connection.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'warehouse'
                  AND table_name = 'dim_venue'
                """
            )
        ).fetchall()
    }


def _seed_legacy_dimension(connection):
    columns = _warehouse_venue_columns(connection)
    if "venue_id" not in columns:
        return

    connection.execute(
        text(
            """
            INSERT INTO manual.venue_registry (
                api_venue_id,
                venue_name,
                venue_address,
                venue_city,
                venue_capacity,
                venue_image_url
            )
            SELECT
                venue_id,
                venue_name,
                venue_address,
                venue_city,
                venue_capacity,
                venue_image_url
            FROM warehouse.dim_venue
            WHERE venue_name IS NOT NULL
            ON CONFLICT (venue_name) DO NOTHING
            """
        )
    )


def _seed_stage_venues(connection):
    connection.execute(
        text(
            """
            INSERT INTO manual.venue_registry (
                api_venue_id,
                venue_name,
                venue_address,
                venue_city,
                venue_capacity,
                venue_image_url
            )
            SELECT DISTINCT ON (venue_name)
                venue_id::bigint,
                venue_name,
                venue_address,
                venue_city,
                venue_capacity::bigint,
                venue_image_url
            FROM stage.venues
            WHERE venue_name IS NOT NULL
            ORDER BY venue_name, venue_id
            ON CONFLICT (venue_name) DO UPDATE SET
                api_venue_id = COALESCE(
                    manual.venue_registry.api_venue_id,
                    EXCLUDED.api_venue_id
                ),
                venue_address = COALESCE(
                    manual.venue_registry.venue_address,
                    EXCLUDED.venue_address
                ),
                venue_city = COALESCE(
                    manual.venue_registry.venue_city,
                    EXCLUDED.venue_city
                ),
                venue_capacity = COALESCE(
                    manual.venue_registry.venue_capacity,
                    EXCLUDED.venue_capacity
                ),
                venue_image_url = COALESCE(
                    manual.venue_registry.venue_image_url,
                    EXCLUDED.venue_image_url
                ),
                updated_at = CURRENT_TIMESTAMP
            """
        )
    )

    connection.execute(
        text(
            """
            INSERT INTO manual.venue_registry (venue_name, venue_city)
            SELECT DISTINCT ON (venue_name)
                venue_name,
                venue_city
            FROM stage.fixtures
            WHERE venue_name IS NOT NULL
            ORDER BY venue_name, fixture_date_utc DESC
            ON CONFLICT (venue_name) DO UPDATE SET
                venue_city = COALESCE(
                    manual.venue_registry.venue_city,
                    EXCLUDED.venue_city
                ),
                updated_at = CURRENT_TIMESTAMP
            """
        )
    )

    connection.execute(
        text(
            """
            INSERT INTO manual.venue_registry (
                venue_name, venue_city, venue_capacity
            )
            SELECT DISTINCT ON (venue_name)
                venue_name,
                venue_city,
                venue_capacity::bigint
            FROM stage.team_seasons
            WHERE venue_name IS NOT NULL
            ORDER BY venue_name, season DESC
            ON CONFLICT (venue_name) DO UPDATE SET
                venue_city = COALESCE(
                    manual.venue_registry.venue_city,
                    EXCLUDED.venue_city
                ),
                venue_capacity = COALESCE(
                    manual.venue_registry.venue_capacity,
                    EXCLUDED.venue_capacity
                ),
                updated_at = CURRENT_TIMESTAMP
            """
        )
    )


def _seed_exact_aliases(connection):
    connection.execute(
        text(
            """
            INSERT INTO manual.venue_name_alias (
                venue_name_raw,
                venue_key,
                review_status,
                match_reason
            )
            SELECT
                source.venue_name,
                registry.venue_key,
                'pending',
                'exact_source_name'
            FROM (
                SELECT DISTINCT venue_name
                FROM stage.fixtures
                WHERE venue_name IS NOT NULL
                UNION
                SELECT DISTINCT venue_name
                FROM stage.team_seasons
                WHERE venue_name IS NOT NULL
            ) source
            JOIN manual.venue_registry registry
                ON registry.venue_name = source.venue_name
            ON CONFLICT (venue_name_raw) DO NOTHING
            """
        )
    )


def _load_reference_venues(connection):
    statement = text(
        """
        INSERT INTO manual.venue_registry (
            api_venue_id,
            venue_name,
            venue_address,
            venue_city,
            venue_capacity,
            venue_image_url,
            review_status
        )
        VALUES (
            :api_venue_id,
            :venue_name,
            :venue_address,
            :venue_city,
            :venue_capacity,
            :venue_image_url,
            :review_status
        )
        ON CONFLICT (venue_name) DO UPDATE SET
            api_venue_id = COALESCE(
                EXCLUDED.api_venue_id,
                manual.venue_registry.api_venue_id
            ),
            venue_address = COALESCE(
                EXCLUDED.venue_address,
                manual.venue_registry.venue_address
            ),
            venue_city = COALESCE(
                EXCLUDED.venue_city,
                manual.venue_registry.venue_city
            ),
            venue_capacity = COALESCE(
                EXCLUDED.venue_capacity,
                manual.venue_registry.venue_capacity
            ),
            venue_image_url = COALESCE(
                EXCLUDED.venue_image_url,
                manual.venue_registry.venue_image_url
            ),
            review_status = EXCLUDED.review_status,
            updated_at = CURRENT_TIMESTAMP
        """
    )

    for row in _read_reference("venues.csv"):
        connection.execute(
            statement,
            {
                "api_venue_id": _optional_int(row["api_venue_id"]),
                "venue_name": row["venue_name"],
                "venue_address": row["venue_address"] or None,
                "venue_city": row["venue_city"] or None,
                "venue_capacity": _optional_int(row["venue_capacity"]),
                "venue_image_url": row["venue_image_url"] or None,
                "review_status": row["review_status"],
            },
        )


def _apply_reference_aliases(connection):
    ensure_canonical = text(
        """
        INSERT INTO manual.venue_registry (venue_name, review_status)
        VALUES (:venue_name_canonical, 'approved')
        ON CONFLICT (venue_name) DO UPDATE SET
            review_status = 'approved',
            updated_at = CURRENT_TIMESTAMP
        RETURNING venue_key
        """
    )
    merge_source_details = text(
        """
        UPDATE manual.venue_registry canonical
        SET api_venue_id = COALESCE(
                canonical.api_venue_id, source.api_venue_id
            ),
            venue_address = COALESCE(
                canonical.venue_address, source.venue_address
            ),
            venue_city = COALESCE(
                canonical.venue_city, source.venue_city
            ),
            venue_capacity = COALESCE(
                canonical.venue_capacity, source.venue_capacity
            ),
            venue_image_url = COALESCE(
                canonical.venue_image_url, source.venue_image_url
            ),
            updated_at = CURRENT_TIMESTAMP
        FROM manual.venue_registry source
        WHERE canonical.venue_key = :venue_key
          AND source.venue_name = :venue_name_raw
        """
    )
    upsert_alias = text(
        """
        INSERT INTO manual.venue_name_alias (
            venue_name_raw,
            venue_key,
            review_status,
            match_reason
        )
        VALUES (
            :venue_name_raw,
            :venue_key,
            :review_status,
            :match_reason
        )
        ON CONFLICT (venue_name_raw) DO UPDATE SET
            venue_key = EXCLUDED.venue_key,
            review_status = EXCLUDED.review_status,
            match_reason = EXCLUDED.match_reason,
            updated_at = CURRENT_TIMESTAMP
        """
    )

    for row in _read_reference("venue_aliases.csv"):
        venue_key = connection.execute(
            ensure_canonical,
            {"venue_name_canonical": row["venue_name_canonical"]},
        ).scalar()
        connection.execute(
            merge_source_details,
            {
                "venue_key": venue_key,
                "venue_name_raw": row["venue_name_raw"],
            },
        )
        connection.execute(
            upsert_alias,
            {
                "venue_name_raw": row["venue_name_raw"],
                "venue_key": venue_key,
                "review_status": row["review_status"],
                "match_reason": row["match_reason"],
            },
        )


def _apply_legacy_corrections(connection):
    connection.execute(
        text(
            """
            UPDATE manual.venue_registry registry
            SET venue_address = COALESCE(
                    correction.venue_address, registry.venue_address
                ),
                venue_city = COALESCE(correction.venue_city, registry.venue_city),
                venue_capacity = COALESCE(
                    correction.venue_capacity, registry.venue_capacity
                ),
                venue_image_url = COALESCE(
                    correction.venue_image_url, registry.venue_image_url
                ),
                updated_at = CURRENT_TIMESTAMP
            FROM manual.venue_corrections correction
            WHERE correction.source_venue_id = correction.canonical_venue_id
              AND registry.api_venue_id = correction.canonical_venue_id
            """
        )
    )


def _approve_reference_identity_aliases(connection):
    connection.execute(
        text(
            """
            UPDATE manual.venue_name_alias alias
            SET review_status = 'approved',
                match_reason = 'canonical_name',
                updated_at = CURRENT_TIMESTAMP
            FROM manual.venue_registry registry
            WHERE registry.venue_key = alias.venue_key
              AND registry.review_status = 'approved'
              AND registry.venue_name = alias.venue_name_raw
            """
        )
    )


def _create_review_view(connection):
    connection.execute(
        text(
            """
            CREATE OR REPLACE VIEW manual.venue_alias_review AS
            SELECT
                alias.venue_name_raw,
                registry.venue_name AS venue_name_canonical,
                alias.review_status,
                alias.match_reason,
                COUNT(fixture.fixture_id) AS number_of_matches,
                MIN(fixture.season) AS first_season,
                MAX(fixture.season) AS last_season,
                STRING_AGG(
                    DISTINCT fixture.venue_city,
                    ' | ' ORDER BY fixture.venue_city
                ) FILTER (WHERE fixture.venue_city IS NOT NULL) AS cities,
                STRING_AGG(
                    DISTINCT fixture.venue_id::text,
                    ' | ' ORDER BY fixture.venue_id::text
                ) FILTER (WHERE fixture.venue_id IS NOT NULL) AS api_venue_ids
            FROM manual.venue_name_alias alias
            JOIN manual.venue_registry registry
                ON registry.venue_key = alias.venue_key
            LEFT JOIN stage.fixtures fixture
                ON fixture.venue_name = alias.venue_name_raw
            GROUP BY
                alias.venue_name_raw,
                registry.venue_name,
                alias.review_status,
                alias.match_reason
            """
        )
    )


def ensure_venue_registry(connection):
    for statement in REGISTRY_SQL:
        connection.execute(text(statement))

    _seed_legacy_dimension(connection)
    _seed_stage_venues(connection)
    _seed_exact_aliases(connection)
    _load_reference_venues(connection)
    _apply_reference_aliases(connection)
    _apply_legacy_corrections(connection)
    _approve_reference_identity_aliases(connection)
    _create_review_view(connection)


def count_pending_venue_aliases(connection):
    return connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM manual.venue_name_alias
            WHERE review_status = 'pending'
            """
        )
    ).scalar()
