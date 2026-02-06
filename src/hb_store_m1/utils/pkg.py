import subprocess
import tempfile
from enum import StrEnum
from pathlib import Path

from hb_store_m1.models.globals import Global
from hb_store_m1.models.output import Output, Status
from hb_store_m1.models.pkg.metadata import EntryKey, ParamSFO
from hb_store_m1.models.pkg.pkg import PKG
from hb_store_m1.models.pkg.validation import ValidationFields, Severity
from hb_store_m1.utils.log import LogUtils


class _PKGToolCommand(StrEnum):
    EXTRACT_PKG_ENTRY = "pkg_extractentry"  # args <input.pkg> <entry_index> <output.*>
    LIST_PKG_ENTRIES = "pkg_listentries"  # args <input.pkg>
    LIST_SFO_ENTRIES = "sfo_listentries"  # args <param.sfo>
    VALIDATE_PKG = "pkg_validate"  # args <input.pkg>


def _run_pkgtool(pkg: Path, command: _PKGToolCommand):
    return subprocess.run(
        [Global.FILES.PKGTOOL_FILE_PATH, command, pkg],
        check=True,
        capture_output=True,
        text=True,
        env={"DOTNET_SYSTEM_GLOBALIZATION_INVARIANT": "1"},
        timeout=120,
    )


class PkgUtils:

    @staticmethod
    def scan():

        LogUtils.log_info("Scanning PKGs...")
        scanned_pkgs = list(
            Path(Global.PATHS.PKG_DIR_PATH).rglob("*.pkg", case_sensitive=False)
        )
        LogUtils.log_info(f"Scanned {len(scanned_pkgs)} packages")

        return scanned_pkgs

    @staticmethod
    def validate(pkg: Path) -> Output:
        validation_result = _run_pkgtool(
            pkg, _PKGToolCommand.VALIDATE_PKG
        ).stdout.splitlines()

        for line in validation_result:
            print(line)
            if "[ERROR]" not in line:
                continue

            for field in ValidationFields:
                name, level = field.value
                if name in line:
                    if level is Severity.CRITICAL:
                        LogUtils.log_error(
                            f"PKG {pkg} validation failed on [{name}] field"
                        )
                        return Output(Status.ERROR, pkg)
                    LogUtils.log_warn(f"PKG {pkg} validation warning on [{name}] field")
                    return Output(Status.WARN, pkg)

        LogUtils.log_debug(f"PKG {pkg} validation successful")
        return Output(Status.OK, pkg)

    # def build_pkg(pkg_path: Path) -> PKG:
    #     pkg = PKG()
    #
    #     # --- listar entries ---
    #     stdout = _run_pkgtool(pkg_path, _PKGToolCommand.LIST_ENTRIES).stdout
    #     lines = stdout.splitlines()
    #
    #     param_index = None
    #
    #     for line in lines[1:]:
    #         parts = line.split()
    #         if len(parts) < 5:
    #             continue
    #
    #         index = int(parts[3])
    #         name = parts[-1]
    #
    #         if name in EntryKey.__members__:
    #             key = EntryKey[name]
    #             pkg.Entries[key] = index
    #
    #             if key is EntryKey.PARAM_SFO:
    #                 param_index = index
    #
    #     # --- extrair PARAM.SFO ---
    #     if param_index is not None:
    #         with tempfile.TemporaryDirectory() as tmp:
    #             out_path = Path(tmp) / "param.sfo"
    #
    #             _run_pkgtool(
    #                 pkg_path,
    #                 _PKGToolCommand.EXTRACT_ENTRY,
    #                 str(param_index),
    #                 str(out_path),
    #             )
    #
    #             raw_sfo = parse_param_sfo(out_path)  # <-- seu parser
    #
    #             for k, v in raw_sfo.items():
    #                 if k in ParamSFO.__members__:
    #                     pkg.ParamSFO[ParamSFO[k]] = v
    #
    #     # --- copiar campos principais ---
    #     pkg.title = str(pkg.ParamSFO.get(ParamSFO.TITLE, ""))
    #     pkg.title_id = str(pkg.ParamSFO.get(ParamSFO.TITLE_ID, ""))
    #     pkg.content_id = str(pkg.ParamSFO.get(ParamSFO.CONTENT_ID, ""))
    #     pkg.category = str(pkg.ParamSFO.get(ParamSFO.CATEGORY, ""))
    #     pkg.version = str(pkg.ParamSFO.get(ParamSFO.VERSION, ""))
    #
    #     pkg.__post_init__()
    #
    #     return pkg


PkgUtils = PkgUtils()
