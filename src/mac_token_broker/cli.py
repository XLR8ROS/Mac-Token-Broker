from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="token-broker")
    parser.add_argument("--version", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.version:
        from . import __version__
        print(__version__)
        return 0
    build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
