"""``triage serve`` (default), ``triage migrate``, ``triage openapi -o FILE``."""

import argparse
import json
import sys
from pathlib import Path

from triage.core.config import RuntimeConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="triage")
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="run the web app and the worker")
    serve.add_argument("--reload", action="store_true", help="reload on code changes (development)")
    sub.add_parser("migrate", help="apply database migrations")
    openapi = sub.add_parser("openapi", help="write the OpenAPI schema")
    openapi.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args(argv)

    config = RuntimeConfig()
    if args.command == "migrate":
        from triage.app.main import run_migrations

        config.data_dir.mkdir(parents=True, exist_ok=True)
        run_migrations(config.database_url)
        return 0
    if args.command == "openapi":
        from triage.app.main import create_app

        schema = create_app(config, start_worker=False).openapi()
        args.output.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
        return 0

    import uvicorn

    uvicorn.run(
        "triage.app.main:create_app",
        factory=True,
        host=config.host,
        port=config.port,
        reload=getattr(args, "reload", False),
        log_config=None,
        access_log=False,
        proxy_headers=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
