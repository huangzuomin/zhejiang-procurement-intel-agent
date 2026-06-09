#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from procurement_intel.qa import answer_question_from_cards_file


def main() -> int:
    args = parse_args()
    print(answer_question_from_cards_file(args.question, args.cards_json))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Answer bounded procurement questions from opportunity_cards.json.")
    parser.add_argument("cards_json", help="Path to generated opportunity_cards.json.")
    parser.add_argument("question", help="Question to answer from known opportunity cards.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
