from football_analytics.load.postgres import build_engine
from football_analytics.load.venue_registry import ensure_venue_registry


def capture_manual_venue_corrections():
    """Mantém compatibilidade com o antigo comando de correções manuais."""
    engine = build_engine()

    with engine.begin() as connection:
        ensure_venue_registry(connection)

    print("Cadastro persistente de estádios e aliases atualizado.")
    print("Novas correções devem ser versionadas na pasta reference.")


if __name__ == "__main__":
    capture_manual_venue_corrections()
