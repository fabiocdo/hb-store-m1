import argparse
import sys

import settings
from index_builder import build_index
from utils.parse_utils import parse_bool
from watcher import watch_pkg_dir


def parse_config():
    parser = argparse.ArgumentParser()
    specs = [
        ("--base-url", {"required": True}),
        ("--auto-generate-json-period", {"required": True, "type": float}),
        ("--auto-rename-pkgs", {"required": True}),
        ("--auto-rename-template", {"required": True}),
        ("--auto-rename-title-mode", {"required": True, "choices": ["none", "uppercase", "lowercase", "capitalize"]}),
    ]
    for flag, opts in specs:
        parser.add_argument(flag, **opts)
    args = parser.parse_args()

    settings.BASE_URL = args.base_url
    settings.AUTO_GENERATE_JSON_PERIOD = args.auto_generate_json_period
    settings.AUTO_RENAME_PKGS = parse_bool(args.auto_rename_pkgs)
    settings.AUTO_RENAME_TEMPLATE = args.auto_rename_template
    settings.AUTO_RENAME_TITLE_MODE = args.auto_rename_title_mode


def main():
    parse_config()
    build_index(False)
    watch_pkg_dir(settings.AUTO_GENERATE_JSON_PERIOD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
