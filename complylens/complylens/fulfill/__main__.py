"""수동 풀필먼트용 CSV 프로파일 CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .profiling import profile_csv
from .summary_ko import render_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Korean CSV data summary")
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)

    profile = profile_csv(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "profile.json").write_text(
        json.dumps(profile.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "summary.html").write_text(
        render_summary(profile),
        encoding="utf-8",
    )
    print(f"created {args.output_dir / 'profile.json'}")
    print(f"created {args.output_dir / 'summary.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
