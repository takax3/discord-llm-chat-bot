from importlib import metadata
from pathlib import Path
import tomllib


PROJECT_NAME = "discord-llm-chat-bot"
PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def get_app_version() -> str:
    try:
        return metadata.version(PROJECT_NAME)
    except metadata.PackageNotFoundError:
        with PYPROJECT_PATH.open("rb") as file:
            project = tomllib.load(file)["project"]
        return str(project["version"])
