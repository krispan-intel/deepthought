"""
services/io_writer.py

Single-writer sink for serializing all file I/O operations.
Prevents race conditions when multiple parallel workers need to write audit logs,
status updates, or TID outputs.

Usage:
    from services.io_writer import IOWriterService

    # Start the writer (typically at service initialization)
    IOWriterService.start()

    # Enqueue write requests from any thread
    IOWriterService.write_jsonl("/path/to/file.jsonl", {"data": "..."})

    # Shutdown gracefully (typically at service exit)
    IOWriterService.shutdown()
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, Optional

from loguru import logger


@dataclass
class WriteRequest:
    """Represents a single write operation."""

    file_path: Path
    content: str
    mode: str = "a"  # "a" for append, "w" for write


class IOWriterService:
    """
    Singleton background writer thread that serializes all file I/O.

    Architecture:
    - Workers enqueue write requests (non-blocking)
    - Writer thread consumes queue and writes sequentially
    - Prevents file handle contention and race conditions
    """

    _instance: Optional[IOWriterService] = None
    _lock = threading.Lock()

    def __init__(self):
        self._queue: Queue[WriteRequest | None] = Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._shutdown_event = threading.Event()

    @classmethod
    def get_instance(cls) -> IOWriterService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def start(cls) -> None:
        """Start the writer thread."""
        instance = cls.get_instance()
        if instance._running:
            logger.warning("IOWriterService already running")
            return

        instance._running = True
        instance._shutdown_event.clear()
        instance._thread = threading.Thread(
            target=instance._worker_loop,
            name="IOWriter",
            daemon=True,
        )
        instance._thread.start()
        logger.info("IOWriterService started")

    @classmethod
    def shutdown(cls, timeout: float = 5.0) -> None:
        """Shutdown the writer thread gracefully."""
        instance = cls.get_instance()
        if not instance._running:
            return

        logger.info("IOWriterService shutdown requested")
        instance._running = False
        instance._queue.put(None)  # Sentinel to wake up worker
        instance._shutdown_event.set()

        if instance._thread and instance._thread.is_alive():
            instance._thread.join(timeout=timeout)
            if instance._thread.is_alive():
                logger.warning("IOWriterService thread did not terminate within timeout")
            else:
                logger.info("IOWriterService shutdown complete")

    @classmethod
    def write_jsonl(cls, file_path: str | Path, record: Dict[str, Any]) -> None:
        """
        Enqueue a JSONL append operation.

        Args:
            file_path: Target file path
            record: Dictionary to serialize as JSON
        """
        instance = cls.get_instance()
        if not instance._running:
            # Fallback: write directly if service not started
            logger.warning(
                "IOWriterService not started, falling back to direct write | file={}",
                file_path,
            )
            cls._direct_write_jsonl(file_path, record)
            return

        path = Path(file_path)
        content = json.dumps(record, ensure_ascii=False) + "\n"
        request = WriteRequest(file_path=path, content=content, mode="a")
        instance._queue.put(request)

    @classmethod
    def write_text(cls, file_path: str | Path, content: str, mode: str = "w") -> None:
        """
        Enqueue a text write operation.

        Args:
            file_path: Target file path
            content: Text content to write
            mode: Write mode ("w" for overwrite, "a" for append)
        """
        instance = cls.get_instance()
        if not instance._running:
            logger.warning(
                "IOWriterService not started, falling back to direct write | file={}",
                file_path,
            )
            cls._direct_write_text(file_path, content, mode)
            return

        path = Path(file_path)
        request = WriteRequest(file_path=path, content=content, mode=mode)
        instance._queue.put(request)

    @classmethod
    def flush(cls, timeout: float = 5.0) -> bool:
        """
        Wait for all pending writes to complete.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if all writes completed, False if timeout
        """
        instance = cls.get_instance()
        if not instance._running:
            return True

        # Wait for queue to be empty
        import time

        start = time.time()
        while time.time() - start < timeout:
            if instance._queue.empty():
                # Give a bit more time for the worker to finish current write
                time.sleep(0.01)
                if instance._queue.empty():
                    return True
            time.sleep(0.01)

        return instance._queue.empty()

    def _worker_loop(self) -> None:
        """Background thread that processes write requests."""
        logger.info("IOWriter worker thread started")
        pending_writes = 0

        while self._running or pending_writes > 0:
            try:
                # Use timeout to allow periodic shutdown check
                timeout = 1.0 if self._running else 0.1
                request = self._queue.get(timeout=timeout)

                if request is None:
                    # Sentinel value for shutdown
                    continue

                pending_writes += 1
                self._execute_write(request)
                pending_writes -= 1

            except Empty:
                # No items in queue, continue
                continue
            except Exception as exc:
                logger.error("IOWriter worker error: {}", exc)
                pending_writes = max(0, pending_writes - 1)

        logger.info("IOWriter worker thread exiting")

    def _execute_write(self, request: WriteRequest) -> None:
        """Execute a single write request."""
        try:
            request.file_path.parent.mkdir(parents=True, exist_ok=True)
            with request.file_path.open(request.mode, encoding="utf-8") as fp:
                fp.write(request.content)
        except Exception as exc:
            logger.error(
                "Failed to write file | path={} | error={}",
                request.file_path,
                exc,
            )

    @staticmethod
    def _direct_write_jsonl(file_path: str | Path, record: Dict[str, Any]) -> None:
        """Direct write fallback for when service is not running."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def _direct_write_text(file_path: str | Path, content: str, mode: str) -> None:
        """Direct write fallback for when service is not running."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open(mode, encoding="utf-8") as fp:
            fp.write(content)
