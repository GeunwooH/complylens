"""ComplyLens local ASGI entrypoint."""
from __future__ import annotations

import os

import uvicorn

from complylens.web.app import app


def main() -> None:
    """Run the ComplyLens FastAPI service for local or simple server deployments."""
    host = os.environ.get("COMPLYLENS_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", os.environ.get("COMPLYLENS_PORT", "8000")))
    uvicorn.run("complylens.web.app:app", host=host, port=port)


if __name__ == "__main__":
    main()
