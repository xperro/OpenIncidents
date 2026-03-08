#!/usr/bin/env python3
"""Local entrypoint for the placeholder Python GCP handler."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from adapters.local import read_input


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cloud", default="gcp")
    parser.add_argument("--input", default="-")
    args = parser.parse_args()

    payload = read_input(args.input)
    result = {
        "handler": "triage-handler",
        "runtime": "python",
        "cloud": args.cloud,
        "entrypoint": "main.py",
        "payload_length": len(payload),
        "cwd": str(pathlib.Path.cwd()),
    }
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
