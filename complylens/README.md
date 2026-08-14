# ComplyLens application

FastAPI service for ComplyLens compliance workflows, including NYC LL144/AEDT bias-audit analysis, report generation, ordering and payment flows, lead capture, and supporting compliance tools.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Install

From the repository root:

```bash
cd complylens
uv sync --locked --all-groups
```

## Run locally

```bash
uv run python main.py
```

The service listens on `0.0.0.0:8000` by default. You can override the bind address with `COMPLYLENS_HOST` and the port with either `PORT` or `COMPLYLENS_PORT`.

You can also run the ASGI app directly:

```bash
uv run uvicorn complylens.web.app:app --host 0.0.0.0 --port 8000
```

## Test

```bash
uv run pytest -q
```

## Core environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `COMPLYLENS_API_KEY` | API key required by protected audit endpoints | none |
| `COMPLYLENS_DATA_DIR` | Directory used for runtime data and generated audit artifacts | `data` |
| `COMPLYLENS_PAYMENT_MODE` | Payment flow: `btc` or `stripe` | `btc` |
| `COMPLYLENS_LLM_ENABLED` | Set to `1` to enable optional LLM narrative generation | disabled |
| `COMPLYLENS_HOST` | Local/server bind host used by `main.py` | `0.0.0.0` |
| `COMPLYLENS_PORT` | Port used by `main.py` when `PORT` is not set | `8000` |

When LLM routing is enabled, configure at least one supported provider key (`DEEPINFRA_API_KEY`, `DIGITALOCEAN_API_KEY`, or `DEEPSEEK_API_KEY`). Payment-provider configuration is only required for the payment mode you actually enable.

## Project layout

- `complylens/audit/` — bias-audit calculations and validation
- `complylens/report/` — report, notice, and public-summary generation
- `complylens/web/` — FastAPI app, billing, orders, leads, and product routes
- `complylens/legal/` — legal/compliance support modules
- `complylens/llm/` — optional LLM routing and narrative generation
- `complylens/receipts/` — receipt and ledger workflows
- `tests/` — pytest suite

> ComplyLens provides informational compliance tooling and is not legal advice. Independent auditor sign-off may be required for a legally effective bias audit.
