"""Entry point: python -m baseball_scorebook."""

from __future__ import annotations

import argparse

from baseball_scorebook.web.server import run_server


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Baseball Scorebook web app.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=None, help="Port to bind. Defaults to a free local port.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the app in a browser.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    run_server(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
    )


if __name__ == "__main__":
    main()
