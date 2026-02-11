from pathlib import Path

from hb_store_m1.models.log import LogModule
from hb_store_m1.models.output import Output, Status
from hb_store_m1.models.pkg.section import Section
from hb_store_m1.utils.file_utils import FileUtils
from hb_store_m1.utils.log_utils import LogUtils


class AutoOrganizer:
    _SECTIONS = {section.name: section for section in Section.ALL}

    @staticmethod
    def _target_dir(app_type: str) -> Path:
        section = AutoOrganizer._SECTIONS.get(app_type, Section.UNKNOWN)
        return section.path

    @staticmethod
    def dry_run(pkg: Path, sfo_data: dict) -> Output:

        if not pkg.is_file():
            return Output(Status.NOT_FOUND, None)

        content_id = str((sfo_data or {}).get("content_id", "").strip())
        if not content_id:
            return Output(Status.INVALID, None)

        invalid_chars = '<>:"/\\|?*'
        if content_id in {".", ".."} or any(ch in content_id for ch in invalid_chars):
            return Output(Status.INVALID, None)

        planned_name = (
            content_id if content_id.lower().endswith(".pkg") else f"{content_id}.pkg"
        )

        app_type = str((sfo_data or {}).get("app_type", "")).strip().lower()
        target_dir = AutoOrganizer._target_dir(app_type)
        target_path = target_dir / planned_name

        if pkg.resolve() == target_path.resolve():
            return Output(Status.SKIP, target_path)

        if target_path.exists():
            return Output(Status.CONFLICT, target_path)

        return Output(Status.OK, target_path)

    @staticmethod
    def run(pkg: Path, sfo_data: dict) -> Path | None:
        output = AutoOrganizer.dry_run(pkg, sfo_data)
        plan_result = output.status
        target_path = output.content if output.content else None

        if plan_result == Status.NOT_FOUND:
            LogUtils.log_error(f"PKG file [{pkg}] not found", LogModule.AUTO_ORGANIZER)
            return None

        if plan_result == Status.INVALID:
            LogUtils.log_error(
                f"Invalid or missing content_id in [{pkg.name}] SFO data",
                LogModule.AUTO_ORGANIZER,
            )
            return None

        if plan_result == Status.SKIP:
            LogUtils.log_debug(
                f"Skipping rename. PKG [{pkg.name}] is already in place",
                LogModule.AUTO_ORGANIZER,
            )
            return target_path

        if plan_result == Status.CONFLICT:
            LogUtils.log_error(
                f"Failed to rename PKG [{pkg.name}]. Target already exists",
                LogModule.AUTO_ORGANIZER,
            )
            return None

        if not target_path:
            LogUtils.log_error(
                f"Failed to resolve target path for {pkg.name}",
                LogModule.AUTO_ORGANIZER,
            )
            return None

        if not FileUtils.move(pkg, target_path, LogModule.AUTO_ORGANIZER):
            return None

        LogUtils.log_info(
            f"PKG {pkg.name} moved successfully to {target_path}",
            LogModule.AUTO_ORGANIZER,
        )
        return target_path
