"""
services/tid_notification_service.py

Email notification service for newly generated TID runs.
"""

from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Set

from loguru import logger

from agents.state import PipelineState
from configs.settings import settings


class TIDNotificationService:
    def __init__(self, state_file: str | None = None):
        self.state_file = Path(state_file) if state_file else settings.data_processed_path / "notified_runs.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def notify_new_tid(self, state: PipelineState) -> bool:
        if not settings.tid_email_notifications_enabled:
            logger.info("TID email notifications disabled by configuration")
            return False

        if not self._smtp_ready():
            logger.info("SMTP not configured, skip TID email notification")
            return False

        if state.run_status not in {"APPROVED", "COMPLETED"}:
            return False

        if not state.output_paths.get("markdown") and not state.output_paths.get("html"):
            return False

        sent = self._load_sent_run_ids()
        if state.run_id in sent:
            return False

        message = self._build_email(state)
        self._send_email(message)
        sent.add(state.run_id)
        self._save_sent_run_ids(sent)
        logger.info(f"TID notification email sent for run_id={state.run_id}")
        return True

    def _smtp_ready(self) -> bool:
        required = [settings.smtp_host, settings.smtp_from, settings.tid_notify_to]
        if not all(item and str(item).strip() for item in required):
            return False
        if settings.smtp_username and not settings.smtp_password:
            return False
        return True

    def _build_email(self, state: PipelineState) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = f"[DeepThought] New TID Generated ({state.run_status})"
        msg["From"] = settings.smtp_from
        msg["To"] = settings.tid_notify_to

        markdown_path = state.output_paths.get("markdown", "")
        html_path = state.output_paths.get("html", "")
        draft_title = ""
        if state.drafts:
            idx = max(0, min(state.selected_draft_index, len(state.drafts) - 1))
            draft_title = state.drafts[idx].title

        body = "\n".join(
            [
                "DeepThought generated a new TID run.",
                "",
                f"Run ID: {state.run_id}",
                f"Status: {state.run_status}",
                f"Domain: {state.domain}",
                f"Target: {state.target}",
                f"Winning Title: {draft_title or 'N/A'}",
                f"Markdown: {markdown_path or 'N/A'}",
                f"HTML: {html_path or 'N/A'}",
            ]
        )
        msg.set_content(body)
        return msg

    def _send_email(self, message: EmailMessage) -> None:
        timeout_seconds = 20
        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout_seconds)
            try:
                server.starttls()
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)
            finally:
                server.quit()
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout_seconds)
            try:
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)
            finally:
                server.quit()

    def _load_sent_run_ids(self) -> Set[str]:
        if not self.state_file.exists():
            return set()
        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return {str(item) for item in payload}
        except Exception:
            logger.warning("Failed to parse notification state file, rebuilding")
        return set()

    def _save_sent_run_ids(self, run_ids: Set[str]) -> None:
        self.state_file.write_text(
            json.dumps(sorted(run_ids), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
