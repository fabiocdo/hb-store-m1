from __future__ import annotations

from src import global_files, global_envs, global_paths


def start() -> None:
    print("GLOBAL_PATHS")
    for k in vars(global_paths):
        print(f"{k}={getattr(global_paths, k)}")

    print("\nGLOBAL_FILES")
    for k in vars(global_files):
        print(f"{k}={getattr(global_files, k)}")

    print("\nGLOBAL_ENVS")
    for k in vars(global_envs):
        print(f"{k}={getattr(global_envs, k)}")

    print("\nSERVER_URL")
    print(global_envs.SERVER_URL)

if __name__ == "__main__":
    start()
