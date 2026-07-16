"""Command line scanner entrypoint."""
from __future__ import annotations
import argparse
import json
from .guard import SecurityGuard

def main() -> None:
    parser = argparse.ArgumentParser(prog="promptsentinel", description="Scan prompts with local PromptSentinel security controls.")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Analyze one prompt")
    scan.add_argument("prompt")
    scan.add_argument("--config", default=None)
    args = parser.parse_args()
    if args.command == "scan": print(json.dumps(SecurityGuard(args.config).analyze(args.prompt), indent=2))
