import json
from pathlib import Path


def save_json(data: dict, filepath: str):

    path = Path(filepath)

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )