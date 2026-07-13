from pathlib import Path


def complete_snapshots(entity_raw_dir, season):
    raw_root = Path(entity_raw_dir).parent
    season_root = raw_root / "snapshots" / str(season)

    if not season_root.exists():
        return []

    return sorted(
        path
        for path in season_root.glob("snapshot_*")
        if path.is_dir() and (path / "_SUCCESS.json").exists()
    )


def latest_complete_snapshot(entity_raw_dir, season):
    complete = complete_snapshots(entity_raw_dir, season)
    return complete[-1] if complete else None
