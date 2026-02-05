from src.models.globals import Global
from src.utils import log_debug
from tabulate import tabulate

def welcome():
    app_title = f"""
█ █ █▀▄     █▀▀ ▀█▀ █▀█ █▀▄ █▀▀     █▄█ ▀█ 
█▀█ █▀▄ ▄▄▄ ▀▀█  █  █ █ █▀▄ █▀▀ ▄▄▄ █ █  █ 
▀ ▀ ▀▀      ▀▀▀  ▀  ▀▀▀ ▀ ▀ ▀▀▀     ▀ ▀ ▀▀▀
v{Global.ENVS.APP_VERSION}
    """
    print(tabulate([[app_title]], tablefmt="rounded_grid"))

def init_directories():
    log_debug("Initializing directories...")

    paths = Global.PATHS
    for p in vars(paths).values():
        p.mkdir(parents=True, exist_ok=True)

    log_debug("Directories OK.")

def start():
    welcome()
    init_directories()

if __name__ == "__main__":
    start()
