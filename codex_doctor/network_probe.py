from __future__ import annotations

import os
import shutil
import socket
import ssl
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .constants import OPENAI_MODELS_URL
from .schemas import NetworkProbe


def proxy_summary() -> dict[str, str]:
    keys = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy"]
    return {key: ("set" if os.environ.get(key) else "unset") for key in keys}


def run_probe(session_id: str | None = None, timeout: int = 10) -> NetworkProbe:
    if shutil.which("curl"):
        return _curl_probe(session_id=session_id, timeout=timeout)
    return _python_probe(session_id=session_id, timeout=timeout)


def _curl_probe(session_id: str | None, timeout: int) -> NetworkProbe:
    command = [
        "curl",
        "-sS",
        "-o",
        "/dev/null",
        "-w",
        "http_code=%{http_code}\n"
        "dns=%{time_namelookup}\n"
        "connect=%{time_connect}\n"
        "tls=%{time_appconnect}\n"
        "ttfb=%{time_starttransfer}\n"
        "total=%{time_total}\n",
        "--max-time",
        str(timeout),
        OPENAI_MODELS_URL,
    ]
    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 2, check=False)
    except subprocess.TimeoutExpired as exc:
        return NetworkProbe(
            session_id=session_id,
            target=OPENAI_MODELS_URL,
            ok=False,
            total_ms=(time.monotonic() - started) * 1000,
            error_type="timeout",
            error_message=str(exc),
            proxy_summary=proxy_summary(),
        )

    data = parse_curl_metrics(result.stdout)
    http_code = int(data["http_code"]) if data.get("http_code", "").isdigit() else None
    ok = http_code in {200, 401, 403} or (result.returncode == 0 and http_code is not None)
    error_type = None
    error_message = None
    if not ok:
        error = (result.stderr or "").lower()
        if "could not resolve" in error:
            error_type = "dns"
        elif "timed out" in error or "timeout" in error:
            error_type = "timeout"
        elif "ssl" in error or "tls" in error:
            error_type = "tls"
        else:
            error_type = "curl"
        error_message = result.stderr.strip()[:500]

    return NetworkProbe(
        session_id=session_id,
        target=OPENAI_MODELS_URL,
        ok=ok,
        http_code=http_code,
        dns_ms=_seconds_to_ms(data.get("dns")),
        connect_ms=_seconds_to_ms(data.get("connect")),
        tls_ms=_seconds_to_ms(data.get("tls")),
        ttfb_ms=_seconds_to_ms(data.get("ttfb")),
        total_ms=_seconds_to_ms(data.get("total")),
        error_type=error_type,
        error_message=error_message,
        proxy_summary=proxy_summary(),
    )


def parse_curl_metrics(output: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def _seconds_to_ms(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value) * 1000
    except ValueError:
        return None


def _python_probe(session_id: str | None, timeout: int) -> NetworkProbe:
    target_host = "api.openai.com"
    started = time.monotonic()
    dns_ms = connect_ms = tls_ms = None
    try:
        dns_started = time.monotonic()
        socket.getaddrinfo(target_host, 443)
        dns_ms = (time.monotonic() - dns_started) * 1000

        connect_started = time.monotonic()
        sock = socket.create_connection((target_host, 443), timeout=timeout)
        connect_ms = (time.monotonic() - connect_started) * 1000

        tls_started = time.monotonic()
        context = ssl.create_default_context()
        wrapped = context.wrap_socket(sock, server_hostname=target_host)
        tls_ms = (time.monotonic() - tls_started) * 1000
        wrapped.close()

        request = Request(OPENAI_MODELS_URL, headers={"User-Agent": "codex-doctor/0.1"})
        http_started = time.monotonic()
        try:
            with urlopen(request, timeout=timeout) as response:
                code = response.status
        except HTTPError as exc:
            code = exc.code
        ttfb_ms = (time.monotonic() - http_started) * 1000
        return NetworkProbe(
            session_id=session_id,
            target=OPENAI_MODELS_URL,
            ok=code in {200, 401, 403},
            http_code=code,
            dns_ms=dns_ms,
            connect_ms=connect_ms,
            tls_ms=tls_ms,
            ttfb_ms=ttfb_ms,
            total_ms=(time.monotonic() - started) * 1000,
            proxy_summary=proxy_summary(),
        )
    except socket.gaierror as exc:
        error_type = "dns"
        error = str(exc)
    except TimeoutError as exc:
        error_type = "timeout"
        error = str(exc)
    except ssl.SSLError as exc:
        error_type = "tls"
        error = str(exc)
    except URLError as exc:
        error_type = "urlopen"
        error = str(exc.reason)
    except OSError as exc:
        error_type = "connect"
        error = str(exc)

    return NetworkProbe(
        session_id=session_id,
        target=OPENAI_MODELS_URL,
        ok=False,
        dns_ms=dns_ms,
        connect_ms=connect_ms,
        tls_ms=tls_ms,
        total_ms=(time.monotonic() - started) * 1000,
        error_type=error_type,
        error_message=error[:500],
        proxy_summary=proxy_summary(),
    )
