#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Production-grade logging module.

Features:
    - 5 standard log levels: DEBUG / INFO / WARNING / ERROR / CRITICAL
    - TimedRotatingFileHandler: true daily rotation + auto-cleanup
    - Lazy singleton initialization via get_logger()
    - Thread-safe colored console output
    - Optional JSON structured logging (for ELK / Loki / Fluentd)
    - Context injection (request_id, trace_id, user_id)
    - Uncaught exception auto-logging via sys.excepthook
    - Duplicate handler prevention
    - Backward compatible: `from log import logger` still works

Usage:
    # Basic (backward compatible)
    from log import logger
    logger.info("Hello")
    logger.error("Something failed", exc_info=True)

    # Advanced
    from log import get_logger, set_log_context, clear_log_context

    logger = get_logger(
        name="myapp",
        level=logging.DEBUG,       # 控制最低输出等级
        json_output=True,          # JSON 格式（生产环境采集用）
        backup_count=60,           # 保留60天日志
        max_bytes=50 * 1024 * 1024 # 单文件最大50MB（超出后当天内也会轮转）
    )

    # 链路追踪
    set_log_context(request_id="req-abc-123", trace_id="trace-xyz")
    logger.info("Processing request")
    clear_log_context()

Log Levels (from lowest to highest):
    DEBUG    (10)  - 开发调试细节，生产环境关闭
    INFO     (20)  - 正常运行信息：启动、完成、状态变更
    WARNING  (30)  - 潜在问题，不影响运行但需关注
    ERROR    (40)  - 功能失败，需要排查
    CRITICAL (50)  - 严重故障，程序可能无法继续
"""

import logging
import os
import sys
import json
import random
import re
import threading
import datetime
import asyncio
import queue
from pathlib import Path
from logging import Handler, LogRecord
from logging.handlers import TimedRotatingFileHandler, QueueHandler, QueueListener
from typing import Optional, Dict, Any
from contextvars import ContextVar

# ============================================================
# ANSI Color Definitions
# ============================================================
COLORS = {
    "RESET":    "\033[0m",
    "GREEN":    "\033[32m",
    "YELLOW":   "\033[33m",
    "CYAN":     "\033[36m",
    "BLUE":     "\033[34m",
    "MAGENTA":  "\033[35m",
    "ERROR":    "\033[1;31;40m",   # 粗体红色 + 黑底
    "CRITICAL": "\033[1;37;41m",   # 粗体白字 + 红底
}

LEVEL_COLORS = {
    logging.DEBUG:    "\033[36m",   # cyan
    logging.INFO:     "\033[32m",   # green
    logging.WARNING:  "\033[33m",   # yellow
    logging.ERROR:    "\033[1;31m", # bold red
    logging.CRITICAL: "\033[1;37;41m",  # white on red
}

NORMAL_COLORS = [COLORS["GREEN"], COLORS["YELLOW"], COLORS["CYAN"],
                 COLORS["BLUE"], COLORS["MAGENTA"]]


# ============================================================
# Custom Handlers
# ============================================================

class ColorStreamHandler(Handler):
    """
    Thread-safe colored console handler.

    Color strategy:
        - ERROR / CRITICAL: fixed red-based colors (always prominent)
        - Other levels: color by level, with random rotation on [+] markers
    """
    terminator = "\n"

    def __init__(self, stream=None, color_by_level: bool = True):
        super().__init__()
        self._stream = stream or sys.stderr
        self._cur_color = COLORS["YELLOW"]
        self._color_lock = threading.Lock()
        self._color_by_level = color_by_level

    def flush(self):
        self.acquire()
        try:
            if self._stream and hasattr(self._stream, "flush"):
                self._stream.flush()
        finally:
            self.release()

    def emit(self, record: LogRecord):
        try:
            msg = self.format(record)
            if self._color_by_level:
                color = LEVEL_COLORS.get(record.levelno, COLORS["RESET"])
            else:
                # Legacy behavior: random color rotation on [+] markers
                if record.levelno >= logging.ERROR:
                    color = COLORS["ERROR"]
                else:
                    color = self._get_color(msg)
            self._stream.write(f"{color}{msg}{COLORS['RESET']}{self.terminator}")
            self.flush()
        except Exception:
            self.handleError(record)

    def _get_color(self, msg: str) -> str:
        if "[+]" not in msg:
            return self._cur_color
        with self._color_lock:
            candidates = [c for c in NORMAL_COLORS if c != self._cur_color]
            self._cur_color = random.choice(candidates)
            return self._cur_color


class SizeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Combined handler: rotates daily at midnight AND when file exceeds max_bytes.
    Prevents single-day log files from growing unbounded in high-throughput services.
    """

    def __init__(self, filename, max_bytes: int = 0, **kwargs):
        super().__init__(filename, **kwargs)
        self.max_bytes = max_bytes

    def shouldRollover(self, record: LogRecord) -> int:
        # Check time-based rotation first
        if super().shouldRollover(record):
            return 1
        # Then check size-based rotation
        if self.max_bytes > 0 and self.stream is not None:
            self.stream.seek(0, 2)  # seek to end
            if self.stream.tell() >= self.max_bytes:
                return 1
        return 0


# ============================================================
# Formatters
# ============================================================

class JsonFormatter(logging.Formatter):
    """
    JSON structured formatter for log aggregation systems.
    Outputs one JSON object per line, compatible with ELK / Loki / Fluentd.
    """

    def format(self, record: LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.datetime.fromtimestamp(
                record.created, tz=datetime.timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno,
            "func": record.funcName,
            "process": record.processName,
            "pid": record.process,
            "thread": record.threadName,
        }

        # Attach context fields
        for key in ("request_id", "trace_id", "user_id"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        # Attach extra fields passed via logger.info("msg", extra={...})
        standard_attrs = set(LogRecord(
            "", 0, "", 0, "", (), None
        ).__dict__.keys()) | {"request_id", "trace_id", "user_id", "message"}
        for key, val in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_entry[key] = val

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            log_entry["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


# ============================================================
# Context Management (asyncio-safe with ContextVar)
# ============================================================

_context = threading.local()
_request_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request_ctx', default=None)


def set_log_context(**kwargs):
    """Set contextual fields for the current thread/async task."""
    for k, v in kwargs.items():
        setattr(_context, k, v)
    _request_ctx.set(kwargs)


def clear_log_context():
    """Clear all contextual fields."""
    _context.__dict__.clear()
    _request_ctx.set(None)


def get_log_context():
    """Get current context (thread-local or async)."""
    ctx = _request_ctx.get()
    if ctx:
        return ctx
    return {k: v for k, v in _context.__dict__.items() if not k.startswith('_')}


class ContextFilter(logging.Filter):
    """Inject thread-local and async context into every log record."""

    CONTEXT_KEYS = ("request_id", "trace_id", "user_id", "session_id")

    def filter(self, record: LogRecord) -> bool:
        # Thread-local context
        for key in self.CONTEXT_KEYS:
            if not hasattr(record, key):
                setattr(record, key, getattr(_context, key, None))

        # Async context
        ctx = _request_ctx.get()
        if ctx:
            for key in self.CONTEXT_KEYS:
                if ctx.get(key) and not getattr(record, key, None):
                    setattr(record, key, ctx[key])
        return True


# ============================================================
# Rate Limiter for Log Sampling
# ============================================================

class LogRateLimiter:
    """Rate limiter to prevent log flooding."""

    def __init__(self, max_per_minute: int = 60):
        self.max_per_minute = max_per_minute
        self._counters: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def should_log(self, key: str) -> bool:
        now = datetime.datetime.now()
        with self._lock:
            if key not in self._counters:
                self._counters[key] = {"count": 1, "reset_at": now + datetime.timedelta(minutes=1)}
                return True

            counter = self._counters[key]
            if now >= counter["reset_at"]:
                counter["count"] = 1
                counter["reset_at"] = now + datetime.timedelta(minutes=1)
                return True

            if counter["count"] < self.max_per_minute:
                counter["count"] += 1
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {k: v["count"] for k, v in self._counters.items()}


_rate_limiter: Optional[LogRateLimiter] = None


def get_rate_limiter(max_per_minute: int = 60) -> LogRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = LogRateLimiter(max_per_minute)
    return _rate_limiter


class RateLimitFilter(logging.Filter):
    """Filter to rate limit specific log patterns."""

    def __init__(self, max_per_minute: int = 60):
        super().__init__()
        self.limiter = LogRateLimiter(max_per_minute)

    def filter(self, record: LogRecord) -> bool:
        key = f"{record.name}:{record.levelno}:{record.funcName}"
        return self.limiter.should_log(key)


# ============================================================
# Logger Factory
# ============================================================

_logger_instance: Optional[logging.Logger] = None
_init_lock = threading.Lock()


def get_logger(
    name: str = "app",
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
    json_output: bool = True,
    backup_count: int = 60,
    max_bytes: int = 50 * 1024 * 1024,  # 50MB default
    console_enabled: bool = True,
    color_by_level: bool = True,
    propagate: bool = False,
    use_queue: bool = True,
    rate_limit: Optional[int] = None,
) -> logging.Logger:
    """
    Get or create the application logger (thread-safe singleton).

    Args:
        name:           Logger name (also used as log filename prefix).
        log_dir:        Log file directory. Default: <project_root>/logs
        level:          Minimum log level (DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50).
        json_output:    True = JSON format for file logs (production log collection).
        backup_count:   Days of log files to retain (default 30).
        max_bytes:      Max single file size before intra-day rotation (0=no size limit).
        console_enabled: Enable colored console output.
        color_by_level: True = color by level; False = legacy random color rotation.
        propagate:      Whether to propagate to parent loggers.

    Returns:
        Configured logging.Logger instance.
    """
    global _logger_instance

    if _logger_instance is not None:
        return _logger_instance

    with _init_lock:
        if _logger_instance is not None:
            return _logger_instance

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = propagate

        # Prevent duplicate handlers
        if logger.handlers:
            _logger_instance = logger
            return logger

        # --- Context filter ---
        logger.addFilter(ContextFilter())

        # --- Log directory ---
        if log_dir is None:
            project_root = Path(__file__).resolve().parent.parent
            log_dir = str(project_root / "logs")
        os.makedirs(log_dir, exist_ok=True)

        # --- File handler: daily rotation + optional size rotation ---
        log_file = os.path.join(log_dir, f"{name}.log")

        if json_output:
            file_formatter = JsonFormatter()
        else:
            file_formatter = logging.Formatter(
                fmt="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        file_handler = SizeTimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=backup_count,
            encoding="utf-8",
            utc=False,
            max_bytes=max_bytes,
        )
        file_handler.suffix = "%Y_%m_%d"
        file_handler.extMatch = re.compile(r"^\.\d{4}_\d{2}_\d{2}$")
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # --- Console handler ---
        if console_enabled:
            env = os.environ.get("PY_ENV", "dev")
            if env == "dev":
                console_fmt = logging.Formatter(
                    fmt="%(asctime)s | %(levelname)-8s | %(message)s  [%(filename)s:%(lineno)d]",
                    datefmt="%H:%M:%S",
                )
            else:
                console_fmt = logging.Formatter(
                    fmt="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )

            console = ColorStreamHandler(color_by_level=color_by_level)
            console.setLevel(level)
            console.setFormatter(console_fmt)
            logger.addHandler(console)

        # --- Rate limit filter ---
        if rate_limit:
            logger.addFilter(RateLimitFilter(rate_limit))

        # --- Queue handler for async performance ---
        if use_queue:
            log_queue = queue.Queue(-1)
            queue_handler = QueueHandler(log_queue)
            queue_handler.setLevel(level)

            # Remove direct handlers, add queue handler
            for h in list(logger.handlers):
                logger.removeHandler(h)

            logger.addHandler(queue_handler)

            # Start listener in background thread
            listener = QueueListener(log_queue, file_handler, console, respect_handler_level=True)
            listener.start()

            # Store listener for cleanup
            logger._queue_listener = listener

        # --- Silence noisy third-party loggers ---
        for noisy_logger in (
            "paramiko", "werkzeug", "apscheduler",
            "urllib3", "httpx", "httpcore",
            "asyncio", "multipart",
        ):
            logging.getLogger(noisy_logger).setLevel(logging.WARNING)

        # --- Global uncaught exception hook ---
        _original_excepthook = sys.excepthook

        def _exception_hook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                _original_excepthook(exc_type, exc_value, exc_tb)
                return
            logger.critical(
                "Uncaught exception",
                exc_info=(exc_type, exc_value, exc_tb),
            )

        sys.excepthook = _exception_hook

        _logger_instance = logger
        return logger


# ============================================================
# Backward-compatible module-level logger
# ============================================================
logger = get_logger()

__all__ = [
    "logger",
    "get_logger",
    "set_log_context",
    "clear_log_context",
    "get_log_context",
    "LogRateLimiter",
    "get_rate_limiter",
]
