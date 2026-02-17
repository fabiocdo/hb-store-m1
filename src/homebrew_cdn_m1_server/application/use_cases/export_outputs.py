from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from homebrew_cdn_m1_server.domain.protocols.logger_port import LoggerPort
from homebrew_cdn_m1_server.domain.protocols.output_exporter_port import OutputExporterPort
from homebrew_cdn_m1_server.domain.protocols.unit_of_work_port import UnitOfWorkPort
from homebrew_cdn_m1_server.config.settings_models import OutputTarget


class ExportOutputs:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWorkPort],
        exporters: Iterable[OutputExporterPort],
        logger: LoggerPort,
    ) -> None:
        self._uow_factory = uow_factory
        self._exporters = {exporter.target: exporter for exporter in exporters}
        self._logger = logger

    def __call__(self, targets: tuple[OutputTarget, ...]) -> tuple[Path, ...]:
        with self._uow_factory() as uow:
            items = uow.catalog.list_items()

        enabled_targets = set(targets)
        exported: list[Path] = []
        for target in targets:
            exporter = self._exporters.get(target)
            if not exporter:
                self._logger.warning("Output target not registered: %s", target.value)
                continue
            files = exporter.export(items)
            exported.extend(files)
            self._logger.info(
                "Exportacao concluida: destino: %s, arquivos: %d",
                target.value,
                len(files),
            )

        for target, exporter in self._exporters.items():
            if target in enabled_targets:
                continue
            removed_files = exporter.cleanup()
            if not removed_files:
                continue
            self._logger.info(
                "Saida desativada removida: destino: %s, arquivos: %d",
                target.value,
                len(removed_files),
            )

        return tuple(exported)
