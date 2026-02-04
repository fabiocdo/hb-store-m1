from __future__ import annotations

from src.models.globals import GlobalEnvs, GlobalFiles, GlobalPaths


def start() -> None:
    gp = GlobalPaths()
    gf = GlobalFiles()
    ge = GlobalEnvs()

    print("GLOBAL_PATHS")
    for k, v in vars(gp).items():
        print(f"{k}={v}")

    print("\nGLOBAL_FILES")
    for k, v in vars(gf).items():
        print(f"{k}={v}")

    print("\nGLOBAL_ENVS")
    for k in dir(ge):
        if k.startswith("_"):
            continue
        v = getattr(ge, k)
        if callable(v):
            continue
        print(f"{k}={v}")


if __name__ == "__main__":
    start()
