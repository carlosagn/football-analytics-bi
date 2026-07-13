from sqlalchemy import text

from football_analytics.load.postgres import build_engine
from football_analytics.load.warehouse import MANUAL_REFERENCE_SQL


CAPTURE_VENUE_CORRECTIONS_SQL = """
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
base AS (
    SELECT DISTINCT ON (venue_id)
        venue_id,
        venue_name,
        venue_address,
        venue_city,
        venue_capacity,
        venue_image_url
    FROM venue_sources
    ORDER BY venue_id, source_priority
)
INSERT INTO manual.venue_corrections (
    source_venue_id,
    canonical_venue_id,
    venue_name,
    venue_address,
    venue_city,
    venue_capacity,
    venue_image_url,
    correction_reason,
    updated_at
)
SELECT
    w.venue_id,
    w.venue_id,
    w.venue_name,
    w.venue_address,
    w.venue_city,
    w.venue_capacity,
    w.venue_image_url,
    'Dados complementados manualmente',
    CURRENT_TIMESTAMP
FROM warehouse.dim_venue w
LEFT JOIN base b ON b.venue_id = w.venue_id
WHERE ROW(
    w.venue_name,
    w.venue_address,
    w.venue_city,
    w.venue_capacity,
    w.venue_image_url
) IS DISTINCT FROM ROW(
    b.venue_name,
    b.venue_address,
    b.venue_city,
    b.venue_capacity,
    b.venue_image_url
)
ON CONFLICT (source_venue_id) DO UPDATE SET
    canonical_venue_id = EXCLUDED.canonical_venue_id,
    venue_name = EXCLUDED.venue_name,
    venue_address = EXCLUDED.venue_address,
    venue_city = EXCLUDED.venue_city,
    venue_capacity = EXCLUDED.venue_capacity,
    venue_image_url = EXCLUDED.venue_image_url,
    correction_reason = EXCLUDED.correction_reason,
    updated_at = CURRENT_TIMESTAMP
"""


DUPLICATE_VENUE_SQL = """
INSERT INTO manual.venue_corrections (
    source_venue_id,
    canonical_venue_id,
    correction_reason,
    updated_at
)
VALUES (
    279,
    19377,
    'Estádio duplicado; 19377 é o identificador canônico',
    CURRENT_TIMESTAMP
)
ON CONFLICT (source_venue_id) DO UPDATE SET
    canonical_venue_id = EXCLUDED.canonical_venue_id,
    correction_reason = EXCLUDED.correction_reason,
    updated_at = CURRENT_TIMESTAMP
"""


def capture_manual_venue_corrections():
    engine = build_engine()

    with engine.begin() as connection:
        for statement in MANUAL_REFERENCE_SQL:
            connection.execute(text(statement))

        captured = connection.execute(
            text(CAPTURE_VENUE_CORRECTIONS_SQL)
        ).rowcount
        connection.execute(text(DUPLICATE_VENUE_SQL))

    print(f"Correções manuais de estádios capturadas: {captured}.")
    print("Mapeamento persistente registrado: 279 -> 19377.")


if __name__ == "__main__":
    capture_manual_venue_corrections()
