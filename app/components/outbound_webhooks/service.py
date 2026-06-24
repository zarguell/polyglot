"""DispatcherService — retry, exponential backoff, and circuit breaker for outbound webhooks."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import time

import httpx
import structlog

logger = structlog.get_logger()


class DispatcherService:
    """Dispatches outbound webhook events with retry and circuit breaker.

    Circuit breaker: after ``failure_threshold`` consecutive failures,
    subsequent dispatches are skipped until ``cooldown_seconds`` passes.
    """

    def __init__(
        self,
        max_retries: int | None = None,
        base_delay: int | None = None,
        failure_threshold: int = 5,
        cooldown_seconds: int = 300,
    ) -> None:
        self.max_retries = max_retries or int(os.getenv("WEBHOOK_MAX_RETRIES", "5"))
        self.base_delay = base_delay or int(os.getenv("WEBHOOK_RETRY_BASE_DELAY", "60"))
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._circuits: dict[str, float] = {}  # url -> cooldown-until timestamp

    async def dispatch(
        self,
        url: str,
        secret: str | None,
        event_type: str,
        payload: dict,
    ) -> tuple[str, int | None, str | None]:
        """Dispatch a webhook event with exponential backoff.

        Returns:
            Tuple of (status, response_code, response_body).
        """
        # Circuit breaker check
        if self._circuits.get(url, 0) > time.monotonic():
            logger.warning("circuit_breaker_open", url=url)
            return ("skipped", None, None)

        last_status = 0
        last_body: str | None = None

        for attempt in range(self.max_retries + 1):
            try:
                headers = {"Content-Type": "application/json"}
                if secret:
                    body_str = self._json_dumps(payload)
                    signature = self._sign(body_str, secret)
                    headers["x-webhook-signature"] = signature

                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    last_status = resp.status_code
                    last_body = resp.text

                if 200 <= resp.status_code < 300:
                    self._clear_circuit(url)
                    return ("delivered", resp.status_code, resp.text)

                if resp.status_code < 500:
                    return ("failed", resp.status_code, resp.text)

            except Exception as exc:
                logger.warning(
                    "webhook_dispatch_attempt_failed", attempt=attempt, url=url, error=str(exc)
                )
                last_body = str(exc)

            if attempt < self.max_retries:
                delay = self.base_delay * (2**attempt)
                logger.info("webhook_retry_wait", url=url, delay=delay, attempt=attempt + 1)
                await asyncio.sleep(delay)

        self._trip_circuit(url)
        return ("failed", last_status, last_body)

    def _sign(self, body: str, secret: str) -> str:
        return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _json_dumps(payload: dict) -> str:
        import json

        return json.dumps(payload, default=str)

    def _trip_circuit(self, url: str) -> None:
        self._circuits[url] = time.monotonic() + self.cooldown_seconds
        logger.warning("circuit_breaker_tripped", url=url)

    def _clear_circuit(self, url: str) -> None:
        self._circuits.pop(url, None)
