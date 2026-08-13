from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "revenue-readiness.py"


def write_manifest(path: Path, **overrides: object) -> Path:
    manifest: dict[str, object] = {
        "offer_id": "kmong-csv-profile-kr",
        "title": "개인정보 제거 CSV 데이터 프로파일 + 한국어 요약",
        "price_krw": 300_000,
        "target_krw": 1_000_000,
        "unit_count_target": 5,
        "deliverable": "프로파일 표와 한국어 요약 리포트",
        "input_policy": "고객이 개인정보를 제거한 CSV만 제출",
        "sells_via": "kmong",
        "cta_path": "/pricing.html?product=kmong-csv-profile",
        "proof_paths": [
            ".omo/evidence/ulw/august-million/c001-offer.md",
            "docs/ops/pricing-strategy.md",
        ],
        "approval_required": True,
    }
    manifest.update(overrides)
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


def run_readiness(manifest: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--manifest", str(manifest)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_incomplete_offer_is_rejected_with_field_errors(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path / "incomplete.json",
        price_krw=None,
        unit_count_target=1,
        cta_path="",
    )

    result = run_readiness(manifest)

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert {"price_krw", "unit_count_target", "cta_path"} <= set(payload["errors"])


def test_complete_offer_is_ready_for_five_orders(tmp_path: Path) -> None:
    result = run_readiness(write_manifest(tmp_path / "complete.json"))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload == {
        "status": "ready",
        "offer_id": "kmong-csv-profile-kr",
        "price_krw": 300_000,
        "target_krw": 1_000_000,
        "unit_count_target": 5,
        "gross_target_krw": 1_500_000,
    }
