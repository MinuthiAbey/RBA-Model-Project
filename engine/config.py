from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def configured_path(name: str) -> Path:
    # The dataset and generated results live outside the code folder; config.yaml says where.
    return (PROJECT_ROOT / load_config()["paths"][name]).resolve()
