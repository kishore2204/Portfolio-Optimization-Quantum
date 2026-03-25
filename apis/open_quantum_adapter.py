"""
Optional Open Quantum provider adapter.

This module is intentionally isolated so the existing pipeline remains unchanged
unless a caller explicitly imports and uses it.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


class OpenQuantumAdapterError(RuntimeError):
    """Raised when adapter configuration or request flow is invalid."""


@dataclass
class OpenQuantumConfig:
    base_url: str
    api_key: str
    submit_path: str = "/v1/jobs"
    api_key_header: str = "Authorization"
    api_key_prefix: str = "Bearer "
    timeout_seconds: int = 30


class OpenQuantumAdapter:
    """
    Tiny HTTP adapter for submitting OpenQASM jobs to a provider endpoint.

    Required environment variables:
    - OPENQUANTUM_BASE_URL
    - OPENQUANTUM_API_KEY

    Optional environment variables:
    - OPENQUANTUM_SUBMIT_PATH (default: /v1/jobs)
    - OPENQUANTUM_API_KEY_HEADER (default: Authorization)
    - OPENQUANTUM_API_KEY_PREFIX (default: Bearer )
    - OPENQUANTUM_TIMEOUT_SECONDS (default: 30)
    """

    def __init__(self, config: OpenQuantumConfig):
        self.config = config

    @classmethod
    def from_env(cls) -> "OpenQuantumAdapter":
        base_url = os.getenv("OPENQUANTUM_BASE_URL", "").strip()
        api_key = os.getenv("OPENQUANTUM_API_KEY", "").strip()

        if not base_url:
            raise OpenQuantumAdapterError(
                "OPENQUANTUM_BASE_URL is missing. Set it to the provider API base URL."
            )
        if not api_key:
            raise OpenQuantumAdapterError(
                "OPENQUANTUM_API_KEY is missing. Set it in your environment; do not hardcode keys."
            )

        submit_path = os.getenv("OPENQUANTUM_SUBMIT_PATH", "/v1/jobs").strip() or "/v1/jobs"
        api_key_header = os.getenv("OPENQUANTUM_API_KEY_HEADER", "Authorization").strip() or "Authorization"
        api_key_prefix = os.getenv("OPENQUANTUM_API_KEY_PREFIX", "Bearer ")

        timeout_raw = os.getenv("OPENQUANTUM_TIMEOUT_SECONDS", "30").strip()
        try:
            timeout_seconds = max(1, int(timeout_raw))
        except ValueError:
            timeout_seconds = 30

        return cls(
            OpenQuantumConfig(
                base_url=base_url.rstrip("/"),
                api_key=api_key,
                submit_path=submit_path,
                api_key_header=api_key_header,
                api_key_prefix=api_key_prefix,
                timeout_seconds=timeout_seconds,
            )
        )

    @staticmethod
    def tiny_openqasm_bell() -> str:
        """Small Bell-state circuit used for smoke testing provider connectivity."""
        return (
            'OPENQASM 2.0;\n'
            'include "qelib1.inc";\n'
            'qreg q[2];\n'
            'creg c[2];\n'
            'h q[0];\n'
            'cx q[0],q[1];\n'
            'measure q -> c;\n'
        )

    def build_tiny_job_payload(self, shots: int = 32, backend: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "job_name": f"portfolio_quantum_smoke_{int(time.time())}",
            "shots": int(shots),
            "circuit": {
                "format": "openqasm2",
                "source": self.tiny_openqasm_bell(),
            },
        }
        if backend:
            payload["backend"] = backend
        return payload

    def submit_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.config.base_url}{self.config.submit_path}"
        body = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            self.config.api_key_header: f"{self.config.api_key_prefix}{self.config.api_key}",
        }

        request = urllib.request.Request(url=url, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                response_text = response.read().decode("utf-8", errors="replace")
                parsed_body = self._parse_response_body(response_text)
                return {
                    "ok": True,
                    "status_code": response.getcode(),
                    "url": url,
                    "response": parsed_body,
                }
        except urllib.error.HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            return {
                "ok": False,
                "status_code": int(error.code),
                "url": url,
                "error": "http_error",
                "response": self._parse_response_body(error_body),
            }
        except urllib.error.URLError as error:
            return {
                "ok": False,
                "status_code": None,
                "url": url,
                "error": "connection_error",
                "message": str(error),
            }

    @staticmethod
    def normalize_submit_result(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce a provider-agnostic summary from heterogeneous API responses.

        This is intentionally heuristic and non-fatal: unknown shapes still return
        a safe summary for artifact-level comparison.
        """
        response = result.get("response")
        if not isinstance(response, dict):
            response = {}

        job_id = (
            response.get("job_id")
            or response.get("id")
            or response.get("task_id")
            or response.get("execution_id")
        )

        status = (
            response.get("status")
            or response.get("state")
            or response.get("job_status")
            or ("submitted" if result.get("ok") else "submission_failed")
        )

        backend = (
            response.get("backend")
            or response.get("backend_name")
            or response.get("device")
            or response.get("target")
        )

        queue_position = (
            response.get("queue_position")
            or response.get("queue")
            or response.get("position")
        )

        return {
            "ok": bool(result.get("ok")),
            "status_code": result.get("status_code"),
            "provider_url": result.get("url"),
            "job_id": job_id,
            "status": status,
            "backend": backend,
            "queue_position": queue_position,
            "error": result.get("error"),
        }

    @staticmethod
    def _parse_response_body(text: str) -> Any:
        text = (text or "").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
