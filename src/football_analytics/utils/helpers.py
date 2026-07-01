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

    return path


def load_json(filepath: str):

    path = Path(filepath)

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)