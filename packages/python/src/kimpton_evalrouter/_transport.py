"""Bounded requests to one explicitly configured API origin."""

from __future__ import annotations

import ipaddress
import json
import math
import os
import random
import re
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlsplit, urlunsplit

import httpx


class ClientError(Exception):
    idempotency_key: str | None = None

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

    def as_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            **(
                {"idempotency_key": self.idempotency_key}
                if self.idempotency_key is not None
                else {}
            ),
        }


class APIError(ClientError):
    def __init__(
        self,
        status: int,
        code: str,
        request_id: str | None = None,
        *,
        message: str | None = None,
        details=None,
    ):
        self.status = status
        self.request_id = request_id
        self.details = details
        super().__init__(code, message or f"API request failed (HTTP {status}, {code}).")

    def as_dict(self):
        return {
            **super().as_dict(),
            "status": self.status,
            "request_id": self.request_id,
            "details": self.details,
        }


class RequestTimeout(ClientError):
    def __init__(self):
        super().__init__(
            "request_timeout",
            "The request deadline expired; a submitted operation may have committed.",
        )


class WaitCancelled(ClientError):
    def __init__(self):
        super().__init__(
            "wait_cancelled",
            "Local waiting was cancelled. The server evaluation was not cancelled.",
        )


@dataclass(frozen=True)
class RequestOptions:
    timeout: float | None = None
    cancel_event: threading.Event | None = None


def positive(value, label):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ClientError("invalid_configuration", f"{label} must be a positive finite number.")
    return float(value)


def segment(value: str):
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z0-9_.:@+-]{1,200}", value)
        or value in {".", ".."}
    ):
        raise ClientError(
            "invalid_input", "Resource identifiers must be nonempty path-safe identifiers."
        )
    return quote(value, safe="")


def normalize_base_url(value, allow_http):
    try:
        parts = urlsplit(value)
        host = parts.hostname
        port = parts.port
        if (
            not host
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
        ):
            raise ValueError()
        if (
            parts.path.rstrip("/") not in {"", "/v1"}
            or "\\" in value
            or any(ord(c) <= 32 for c in value)
        ):
            raise ValueError()
        local = host == "localhost"
        with suppress(ValueError):
            local = local or ipaddress.ip_address(host).is_loopback
        if parts.scheme != "https" and not (parts.scheme == "http" and allow_http and local):
            raise ValueError()
        if port is not None and not 1 <= port <= 65535:
            raise ValueError()
        return urlunsplit((parts.scheme, parts.netloc, "/v1", "", ""))
    except (TypeError, ValueError):
        raise ClientError(
            "invalid_configuration",
            "Set an HTTPS API origin or /v1 URL. Explicit HTTP is allowed only for loopback development.",
        ) from None


def checkpoint(deadline, cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise WaitCancelled()
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RequestTimeout()
    return remaining


def pause(delay, deadline, cancel_event):
    remaining = checkpoint(deadline, cancel_event)
    seconds = min(delay, remaining)
    if cancel_event is not None:
        if cancel_event.wait(seconds):
            raise WaitCancelled()
    else:
        time.sleep(seconds)
    checkpoint(deadline, cancel_event)


def retry_delay(attempt, header):
    delay = min(5, 0.25 * 2**attempt) + random.random() * 0.25
    if header and len(header) < 100:
        try:
            suggested = float(header)
        except ValueError:
            try:
                suggested = (parsedate_to_datetime(header) - datetime.now(UTC)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                suggested = 0
        if math.isfinite(suggested):
            delay = max(delay, suggested)
    return delay


def secret_values(body):
    values = []
    if isinstance(body, dict):
        for key, value in body.items():
            if (
                isinstance(key, str)
                and re.search(r"key|secret|token|password", key, re.I)
                and isinstance(value, str)
                and value
            ):
                values.append(value)
            values.extend(secret_values(value))
    elif isinstance(body, list):
        for value in body:
            values.extend(secret_values(value))
    return values


def safe_error_value(value, secrets, depth=0):
    if depth > 4:
        return "[truncated]"
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[redacted]")
        return "".join(c if c.isprintable() else " " for c in value)[:2000]
    if isinstance(value, dict):
        return {
            safe_error_value(str(key), secrets)[:100]: "[redacted]"
            if re.search(r"key|secret|token|password|authorization|cookie", str(key), re.I)
            else safe_error_value(item, secrets, depth + 1)
            for key, item in list(value.items())[:100]
        }
    if isinstance(value, list):
        return [safe_error_value(item, secrets, depth + 1) for item in value[:100]]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value if value is None or type(value) in {int, float, bool} else None


def reject_constant(_value):
    raise ValueError("Non-finite JSON number")


class Transport:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        workspace_id: str | None = None,
        timeout: float = 120,
        request_timeout: float = 30,
        max_retries: int = 2,
        max_response_bytes: int = 64 * 1024 * 1024,
        max_export_bytes: int = 256 * 1024 * 1024,
        allow_http: bool = False,
        transport: httpx.BaseTransport | None = None,
    ):
        self._base = normalize_base_url(
            base_url or os.environ.get("EVALROUTER_BASE_URL", ""), allow_http
        )
        self._key = api_key if api_key is not None else os.environ.get("EVALROUTER_API_KEY")
        self._workspace = (
            workspace_id if workspace_id is not None else os.environ.get("EVALROUTER_WORKSPACE_ID")
        )
        for label, value in (("API key", self._key), ("Workspace ID", self._workspace)):
            if value is not None and (
                not isinstance(value, str)
                or not 1 <= len(value) <= 4096
                or any(not 33 <= ord(c) <= 126 for c in value)
            ):
                raise ClientError(
                    "invalid_configuration", f"{label} must be printable non-space ASCII."
                )
        self.timeout = positive(timeout, "Timeout")
        self.request_timeout = positive(request_timeout, "Request timeout")
        if type(max_retries) is not int or not 0 <= max_retries <= 5:
            raise ClientError("invalid_configuration", "max_retries must be between 0 and 5.")
        self.max_retries = max_retries
        for value in (max_response_bytes, max_export_bytes):
            if type(value) is not int or value < 1:
                raise ClientError(
                    "invalid_configuration", "Response size limits must be positive integers."
                )
        self.max_response_bytes = max_response_bytes
        self.max_export_bytes = max_export_bytes
        self._http = httpx.Client(follow_redirects=False, trust_env=False, transport=transport)

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def request(
        self,
        method,
        path,
        *,
        body=None,
        query=None,
        retry=False,
        idempotency_key=None,
        binary=False,
        options=None,
    ):
        options = options or RequestOptions()
        deadline = time.monotonic() + positive(
            options.timeout if options.timeout is not None else self.timeout, "Timeout"
        )
        if not path.startswith("/") or path.startswith("//"):
            raise ClientError("invalid_input", "Invalid API resource path.")
        headers = {
            "Accept": "*/*" if binary else "application/json",
            "User-Agent": "kimpton-evalrouter-python/0.1.0",
        }
        if self._key:
            headers["Authorization"] = f"Bearer {self._key}"
        if self._workspace:
            headers["X-Workspace-Id"] = self._workspace
        if idempotency_key is not None:
            if (
                not isinstance(idempotency_key, str)
                or not 1 <= len(idempotency_key) <= 128
                or any(not 32 <= ord(c) <= 126 for c in idempotency_key)
            ):
                raise ClientError(
                    "invalid_input",
                    "Idempotency keys must contain 1–128 printable ASCII characters.",
                )
            headers["Idempotency-Key"] = idempotency_key
        try:
            content = (
                None
                if body is None
                else json.dumps(
                    body, ensure_ascii=False, allow_nan=False, separators=(",", ":")
                ).encode()
            )
            parameters = {
                key: str(value).lower() if isinstance(value, bool) else value
                for key, value in (query or {}).items()
                if value is not None
            }
        except (TypeError, ValueError, AttributeError):
            raise ClientError("invalid_input", "Request data must be JSON-serializable.") from None
        if content is not None:
            headers["Content-Type"] = "application/json"
        secrets = [value for value in [self._key, *secret_values(body)] if value]
        for attempt in range(self.max_retries + 1):
            remaining = checkpoint(deadline, options.cancel_event)
            delay = retry_delay(attempt, None)
            error = None
            try:
                with self._http.stream(
                    method,
                    self._base + path,
                    params=parameters,
                    headers=headers,
                    content=content,
                    timeout=min(self.request_timeout, remaining),
                    follow_redirects=False,
                ) as response:
                    checkpoint(deadline, options.cancel_event)
                    if 300 <= response.status_code < 400:
                        raise APIError(response.status_code, "redirect_rejected")
                    chunks, size = [], 0
                    maximum = (
                        (self.max_export_bytes if binary else self.max_response_bytes)
                        if response.is_success
                        else 65536
                    )
                    for chunk in response.iter_bytes():
                        checkpoint(deadline, options.cancel_event)
                        size += len(chunk)
                        if size > maximum:
                            raise ClientError(
                                "response_too_large",
                                "API response exceeds the configured size limit.",
                            )
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                    checkpoint(deadline, options.cancel_event)
                    if response.is_success:
                        if binary:
                            return raw
                        try:
                            result = json.loads(raw, parse_constant=reject_constant)
                            if not isinstance(result, dict):
                                raise ValueError()
                        except (ValueError, UnicodeError):
                            raise ClientError(
                                "invalid_response", "API returned an invalid JSON object."
                            ) from None
                        checkpoint(deadline, options.cancel_event)
                        return result
                    code, request_id = "http_error", response.headers.get("X-Request-Id")
                    message, details = None, None
                    try:
                        server_error = json.loads(raw).get("error", {})
                        candidate = server_error.get("code")
                        if isinstance(candidate, str) and re.fullmatch(
                            r"[a-z][a-z0-9_]{0,99}", candidate
                        ):
                            code = candidate
                        if isinstance(server_error.get("message"), str):
                            message = safe_error_value(server_error["message"], secrets)
                        details = safe_error_value(server_error.get("details"), secrets)
                    except (ValueError, AttributeError, UnicodeError):
                        pass
                    if any(value in code for value in secrets):
                        code = "http_error"
                    if (
                        not request_id
                        or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", request_id)
                        or any(value in request_id for value in secrets)
                    ):
                        request_id = None
                    error = APIError(
                        response.status_code, code, request_id, message=message, details=details
                    )
                    if response.status_code not in {429, 502, 503, 504}:
                        raise error
                    delay = retry_delay(attempt, response.headers.get("Retry-After"))
            except httpx.TransportError:
                checkpoint(deadline, options.cancel_event)
                error = ClientError(
                    "network_error",
                    "The API request failed; a submitted operation may have committed.",
                )
            if not retry or attempt == self.max_retries:
                raise error from None
            pause(delay, deadline, options.cancel_event)
        raise AssertionError("Unreachable retry state")


class Resource:
    def __init__(self, client: Transport):
        self._client = client
