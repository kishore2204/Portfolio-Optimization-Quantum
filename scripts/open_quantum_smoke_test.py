"""
Submit one tiny OpenQASM job to an optional Open Quantum provider endpoint.

This script is standalone and does not alter the existing optimization pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

# Ensure workspace root is importable when script is executed directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apis.open_quantum_adapter import OpenQuantumAdapter, OpenQuantumAdapterError


def build_output_payload(
    request_payload: Dict[str, Any],
    submit_result: Dict[str, Any],
    normalized_result: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "request_payload": request_payload,
        "submit_result": submit_result,
        "normalized_submit_result": normalized_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Open Quantum tiny-job smoke test")
    parser.add_argument("--shots", type=int, default=32, help="Measurement shots")
    parser.add_argument("--backend", type=str, default=None, help="Optional provider backend name")
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Optional explicit output path for the artifact JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not submit; only generate and save payload preview.",
    )
    args = parser.parse_args()

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output) if args.output else Path("results") / f"open_quantum_smoke_test_{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        adapter = OpenQuantumAdapter.from_env()
    except OpenQuantumAdapterError as error:
        print(f"[ERROR] {error}")
        print("Hint: set OPENQUANTUM_BASE_URL and OPENQUANTUM_API_KEY in your shell environment.")
        return 2

    request_payload = adapter.build_tiny_job_payload(shots=args.shots, backend=args.backend)

    if args.dry_run:
        submit_result = {
            "ok": True,
            "dry_run": True,
            "message": "Submission skipped. Payload generated successfully.",
        }
    else:
        submit_result = adapter.submit_job(request_payload)

    normalized_result = adapter.normalize_submit_result(submit_result)

    artifact = build_output_payload(
        request_payload=request_payload,
        submit_result=submit_result,
        normalized_result=normalized_result,
    )
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2)

    if submit_result.get("ok"):
        print(f"[OK] Smoke test artifact written: {output_path}")
        return 0

    print(f"[WARN] Provider submission returned a non-success result. Artifact: {output_path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
