from __future__ import annotations

import logging
from pathlib import Path

from homebrew_cdn_m1_server.domain.protocols.unit_of_work_port import UnitOfWorkPort
from homebrew_cdn_m1_server.application.use_cases.export_outputs import ExportOutputs
from homebrew_cdn_m1_server.application.use_cases.ingest_package import IngestPackage
from homebrew_cdn_m1_server.application.use_cases.reconcile_catalog import ReconcileCatalog
from homebrew_cdn_m1_server.config.settings_models import AppConfig
from homebrew_cdn_m1_server.infrastructure.exporters.fpkgi_json_exporter import FpkgiJsonExporter
from homebrew_cdn_m1_server.infrastructure.exporters.store_db_exporter import StoreDbExporter
from homebrew_cdn_m1_server.infrastructure.gateways.pkgtool_gateway import PkgtoolGateway
from homebrew_cdn_m1_server.infrastructure.locking.file_lock_adapter import FileLockAdapter
from homebrew_cdn_m1_server.infrastructure.repositories.fs_package_store import FsPackageStore
from homebrew_cdn_m1_server.infrastructure.repositories.json_snapshot_store import JsonSnapshotStore
from homebrew_cdn_m1_server.infrastructure.repositories.sqlite_unit_of_work import SqliteUnitOfWork


class Container:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.logger = logging.getLogger("homebrew_cdn_m1_server")

        self.package_store = FsPackageStore(config.paths)
        self.snapshot_store = JsonSnapshotStore(config.paths.snapshot_path)
        self.lock = FileLockAdapter(str(config.paths.cache_dir / "reconcile.lock"), timeout_seconds=0.0)
        self.pkgtool = PkgtoolGateway(
            pkgtool_bin=config.paths.pkgtool_bin_path,
            timeout_seconds=config.user.pkgtool_timeout_seconds,
            media_dir=config.paths.media_dir,
        )

    def uow_factory(self) -> UnitOfWorkPort:
        return SqliteUnitOfWork(self.config.paths.catalog_db_path)

    def initialize(self) -> None:
        self.package_store.ensure_layout()
        self.package_store.ensure_public_index(self.config.paths.init_dir / "index.html")
        init_sql = self._read_init_sql(self.config.paths.init_dir / "catalog_db.sql")
        with self.uow_factory() as uow:
            uow.catalog.init_schema(init_sql)
            uow.commit()

    @staticmethod
    def _read_init_sql(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"Catalog schema not found: {path}")
        sql = path.read_text("utf-8").strip()
        if not sql:
            raise ValueError(f"Catalog schema file is empty: {path}")
        return sql

    def build_reconcile_use_case(self) -> ReconcileCatalog:
        ingest = IngestPackage(
            uow_factory=self.uow_factory,
            package_probe=self.pkgtool,
            package_store=self.package_store,
            logger=self.logger,
        )

        exporters = [
            StoreDbExporter(
                output_db_path=self.config.paths.store_db_path,
                init_sql_path=self.config.paths.init_dir / "store_db.sql",
                base_url=self.config.base_url,
            ),
            FpkgiJsonExporter(
                output_dir=self.config.paths.fpkgi_share_dir,
                base_url=self.config.base_url,
            ),
        ]

        export_outputs = ExportOutputs(
            uow_factory=self.uow_factory,
            exporters=exporters,
            logger=self.logger,
        )

        return ReconcileCatalog(
            uow_factory=self.uow_factory,
            package_store=self.package_store,
            snapshot_store=self.snapshot_store,
            ingest_package=ingest,
            export_outputs=export_outputs,
            lock=self.lock,
            logger=self.logger,
            worker_count=self.config.user.watcher_pkg_preprocess_workers,
            output_targets=self.config.user.output_targets,
        )
