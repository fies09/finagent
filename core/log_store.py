import logging
import sqlite3
import sys
from typing import Any

from loguru import logger

from .store import DataStore


class _DbHandler(logging.Handler):
    def __init__(self, store: DataStore):
        super().__init__(level=logging.INFO)
        self.store = store
        self._LEVEL_MAP = {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO",
            logging.WARNING: "WARNING",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "ERROR",
        }

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = self._LEVEL_MAP.get(record.levelno, "INFO")
            msg = self.format(record)
            with sqlite3.connect(self.store.db_path) as conn:
                conn.execute(
                    "INSERT INTO system_logs (level, message, source) VALUES (?, ?, ?)",
                    (level, msg[:2000], record.name),
                )
                conn.execute(
                    "DELETE FROM system_logs WHERE id < (SELECT MAX(id) - 1000 FROM system_logs)"
                )
                conn.commit()
        except Exception:
            self.handleError(record)


class LogStore:
    def __init__(self, store: DataStore | None = None):
        self.store = store or DataStore()
        self._listener_installed = False

    def install_listener(self) -> None:
        if self._listener_installed:
            return
        try:
            std_logger = logging.getLogger()
            handler = _DbHandler(self.store)
            handler.setFormatter(logging.Formatter("%(message)s"))
            std_logger.addHandler(handler)
            self._handler = handler
            self._listener_installed = True
            _install_post_queue_hook(handler)
            std_logger.info("LogStore listener installed")
        except Exception as e:
            print(f"LogStore install failed: {e}")


def _install_post_queue_hook(handler: logging.Handler) -> None:
    """log.py 的 QueueListener 启动时接管了所有 handler；
    这里把新 handler 主动注入到 listener 的 handlers 列表中。"""
    try:
        for v in logging.Logger.manager.loggerDict.values():
            lg = v if isinstance(v, logging.Logger) else None
            if lg is None:
                continue
            listener = getattr(lg, "_queue_listener", None)
            if listener and handler not in listener.handlers:
                listener.handlers = tuple(list(listener.handlers) + [handler])
    except Exception:
        pass


class LogStore:
    def __init__(self, store: DataStore | None = None):
        self.store = store or DataStore()
        self._listener_installed = False

    def install_listener(self) -> None:
        if self._listener_installed:
            return
        try:
            std_logger = logging.getLogger()
            handler = _DbHandler(self.store)
            handler.setFormatter(logging.Formatter("%(message)s"))
            std_logger.addHandler(handler)
            self._handler = handler
            self._listener_installed = True
            _install_post_queue_hook(handler)
            std_logger.info("LogStore listener installed")
        except Exception as e:
            print(f"LogStore install failed: {e}")

    def list_logs(self, level: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT id, level, message, source, created_at FROM system_logs"
        params: list = []
        if level:
            query += " WHERE level = ?"
            params.append(level.upper())
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def clear(self) -> None:
        with sqlite3.connect(self.store.db_path) as conn:
            conn.execute("DELETE FROM system_logs")
            conn.commit()