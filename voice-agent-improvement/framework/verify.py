"""Run reproducible project verification and write a timestamped evidence artifact."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.core.io import write_json


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT.parent / "dashboard"
OUTPUT_ROOT = ROOT / "artifacts" / "framework" / "verification"
SECRET_PATTERNS = [re.compile(r"sk_samvaad_[A-Za-z0-9_-]+"), re.compile(r"AIza[0-9A-Za-z_-]{20,}")]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(name: str, command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    combined = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    return {
        "name": name,
        "command": command,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "output_tail": combined[-3000:],
    }


def _resolve_frozen_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else (ROOT / path).resolve()


def _check_frozen_items(items: list[tuple[str, dict[str, str]]]) -> list[dict[str, Any]]:
    checked = []
    for label, item in items:
        path = _resolve_frozen_path(item["path"])
        actual = _sha(path) if path.exists() else None
        checked.append(
            {
                "component": label,
                "path": str(path),
                "expected": item["sha256"],
                "actual": actual,
                "matched": actual == item["sha256"],
            }
        )
    return checked


def _historical_freeze_check() -> dict[str, Any]:
    """Verify immutable experiment inputs without pretending the old evaluator is current.

    ``method_freeze.json`` sealed the text-final experiment. Its baseline,
    finalist, selection decision, and data split must remain byte-identical.
    The evaluator implementation has since evolved for live audio and is frozen
    independently below. Evaluator drift is therefore reported explicitly but
    does not invalidate the already-completed historical experiment.
    """
    freeze_path = ROOT / "artifacts" / "framework" / "emi" / "method_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    immutable_items: list[tuple[str, dict[str, str]]] = []
    for label in ("baseline_prompt", "finalist_prompt", "selection_decision"):
        immutable_items.append((label, freeze["components"][label]))
    immutable_items.extend(("development_suite", item) for item in freeze["components"]["development_suite"])
    immutable = _check_frozen_items(immutable_items)
    historical_evaluator = _check_frozen_items(
        [("historical_evaluator_files", item) for item in freeze["components"]["evaluator_files"]]
    )
    exact_historical_match = all(item["matched"] for item in immutable + historical_evaluator)
    return {
        "passed": all(item["matched"] for item in immutable),
        "status": "superseded_evaluator_reported" if not exact_historical_match else "exact_historical_match",
        "exact_historical_match": exact_historical_match,
        "immutable_experiment_inputs": immutable,
        "historical_evaluator_files": historical_evaluator,
        "supersession_note": (
            "The text-final experiment remains frozen. Current live evaluation uses the separately "
            "versioned V7 evaluator; mismatches below are disclosed evolution, not rewritten history."
        ),
    }


def _live_evaluator_freeze_check() -> dict[str, Any]:
    freeze_path = ROOT / "artifacts" / "framework" / "emi" / "eva_adapter_v10" / "evaluator_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    items: list[tuple[str, dict[str, str]]] = []
    for collection in ("evaluator_files", "scenario_suite", "live_voice_suite"):
        items.extend((collection, item) for item in freeze["components"][collection])
    checked = _check_frozen_items(items)
    return {
        "passed": all(item["matched"] for item in checked),
        "evaluator_version": freeze["evaluator_version"],
        "bundle_sha256": freeze["bundle_sha256"],
        "components": checked,
    }


def _fresh_final_check() -> dict[str, Any]:
    root = ROOT / "artifacts" / "framework" / "emi"
    scenario_root = root / "dynamic_scenarios_v1"
    seal = json.loads((scenario_root / "fresh_final_seal.json").read_text(encoding="utf-8"))
    access = json.loads((scenario_root / "fresh_final_access_log.json").read_text(encoding="utf-8"))
    decision = json.loads((root / "fresh_final_decision.json").read_text(encoding="utf-8"))
    dataset_path = scenario_root / "fresh_final.jsonl"
    return {
        "passed": (
            _sha(dataset_path) == seal["dataset_sha256"]
            and len(access.get("evaluation_runs", [])) == 2
            and decision.get("protocol_valid") is True
            and decision.get("decision") == "pass_text_final_awaiting_matched_voice"
        ),
        "dataset_sha256": _sha(dataset_path),
        "sealed_sha256": seal["dataset_sha256"],
        "evaluation_runs": len(access.get("evaluation_runs", [])),
        "decision": decision.get("decision"),
    }


def _secret_scan() -> dict[str, Any]:
    roots = [
        ROOT / "framework",
        ROOT / "agent",
        ROOT / "README.md",
        ROOT.parent / "handoff.md",
        ROOT.parent / "FINAL-EXECUTION-REPORT.html",
        DASHBOARD / "app",
        DASHBOARD / "public",
    ]
    hits = []
    for root in roots:
        paths = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                hits.append(str(path))
    return {"passed": not hits, "credential_pattern_files": hits}


def verify(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    checks = [
        _run("python_unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-q"], ROOT),
        _run("dashboard_lint", ["npm", "run", "lint"], DASHBOARD),
        _run("dashboard_tests", ["npm", "test"], DASHBOARD),
        _run("dashboard_build", ["npm", "run", "build"], DASHBOARD),
    ]
    historical_freeze = _historical_freeze_check()
    live_freeze = _live_evaluator_freeze_check()
    fresh = _fresh_final_check()
    secrets = _secret_scan()
    passed = (
        all(item["passed"] for item in checks)
        and historical_freeze["passed"]
        and live_freeze["passed"]
        and fresh["passed"]
        and secrets["passed"]
    )
    now = datetime.now(UTC)
    record = {
        "schema_version": "loopline-verification.v2",
        "verified_at": now.isoformat(),
        "passed": passed,
        "commands": checks,
        "historical_method_freeze": historical_freeze,
        "live_evaluator_freeze": live_freeze,
        "fresh_final_protocol": fresh,
        "secret_scan": secrets,
        "environment": {"python": sys.version.split()[0], "node_path": os.environ.get("PATH", "").split(os.pathsep)[0]},
    }
    timestamped = output_root / f"verification-{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    write_json(timestamped, record)
    write_json(output_root / "latest.json", record)
    return record


if __name__ == "__main__":
    result = verify()
    print(json.dumps({"passed": result["passed"], "verified_at": result["verified_at"], "checks": {item["name"]: item["passed"] for item in result["commands"]}}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
