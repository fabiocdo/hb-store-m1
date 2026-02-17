from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from homebrew_cdn_m1_server.domain.workflows.models.reconcile_result import ReconcileResult
from homebrew_cdn_m1_server.domain.protocols.lock_port import LockPort
from homebrew_cdn_m1_server.domain.protocols.logger_port import LoggerPort
from homebrew_cdn_m1_server.domain.protocols.package_store_port import PackageStorePort
from homebrew_cdn_m1_server.domain.protocols.snapshot_store_port import SnapshotStorePort
from homebrew_cdn_m1_server.domain.protocols.unit_of_work_port import UnitOfWorkPort
from homebrew_cdn_m1_server.domain.workflows.export_outputs import ExportOutputs
from homebrew_cdn_m1_server.domain.workflows.ingest_package import IngestPackage, IngestResult
from homebrew_cdn_m1_server.config.settings_models import OutputTarget
from homebrew_cdn_m1_server.domain.services.package_diff import build_delta


class ReconcileCatalog:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWorkPort],
        package_store: PackageStorePort,
        snapshot_store: SnapshotStorePort,
        ingest_package: IngestPackage,
        export_outputs: ExportOutputs,
        lock: LockPort,
        logger: LoggerPort,
        worker_count: int,
        output_targets: tuple[OutputTarget, ...],
    ) -> None:
        self._uow_factory = uow_factory
        self._package_store = package_store
        self._snapshot_store = snapshot_store
        self._ingest_package = ingest_package
        self._export_outputs = export_outputs
        self._lock = lock
        self._logger = logger
        self._worker_count = max(1, int(worker_count))
        self._output_targets = output_targets

    def _build_snapshot(self) -> dict[str, tuple[int, int]]:
        snapshot: dict[str, tuple[int, int]] = {}
        for pkg_path in self._package_store.scan_pkg_files():
            try:
                snapshot[str(pkg_path)] = self._package_store.stat(pkg_path)
            except OSError:
                continue
        return snapshot

    @staticmethod
    def _split_results(paths: list[str], results: list[IngestResult]) -> tuple[int, int, int]:
        failures = sum(1 for item in results if item.item is None)
        added = max(0, len(paths) - failures)
        return added, 0, failures

    def _ingest_candidates(self, candidates: list[Path]) -> tuple[int, int, int]:
        if not candidates:
            return 0, 0, 0

        if self._worker_count <= 1 or len(candidates) == 1:
            results = [self._ingest_package(path) for path in candidates]
            return self._split_results([str(p) for p in candidates], results)

        results: list[IngestResult] = []
        with ThreadPoolExecutor(max_workers=self._worker_count) as executor:
            future_by_path = {
                executor.submit(self._ingest_package, path): path for path in candidates
            }
            for future in as_completed(future_by_path):
                path = future_by_path[future]
                try:
                    results.append(future.result())
                except Exception:
                    self._logger.error(
                        "Unexpected ingest worker failure for %s\n%s",
                        path,
                        traceback.format_exc(),
                    )
                    results.append(IngestResult(item=None, created=False, updated=False))
        return self._split_results([str(p) for p in candidates], results)

    def __call__(self) -> ReconcileResult:
        if not self._lock.acquire():
            self._logger.warning("Reconcile skipped: another cycle is still running")
            return ReconcileResult(0, 0, 0, 0, tuple())

        try:
            previous = dict(self._snapshot_store.load())
            current = self._build_snapshot()
            delta = build_delta(previous, current)

            candidates = [Path(path) for path in (*delta.added, *delta.updated)]
            added, updated, failed = self._ingest_candidates(candidates)

            final_snapshot = self._build_snapshot()
            existing_paths = set(final_snapshot)

            with self._uow_factory() as uow:
                removed = uow.catalog.delete_by_pkg_paths_not_in(existing_paths)
                uow.commit()

            exported_files = self._export_outputs(self._output_targets)
            self._snapshot_store.save(final_snapshot)

            self._logger.info(
                "Sincronizacao concluida: adicionados: %d, atualizados: %d, removidos: %d, falhas: %d, exportados: %d",
                added,
                updated,
                removed,
                failed,
                len(exported_files),
            )
            return ReconcileResult(
                added=added,
                updated=updated,
                removed=removed,
                failed=failed,
                exported_files=exported_files,
            )
        finally:
            self._lock.release()
