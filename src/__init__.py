from pathlib import Path

from src.models.globals import GlobalPaths

def init_directories() -> None:
    for path in vars(GlobalPaths).values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)


# init_directories()
