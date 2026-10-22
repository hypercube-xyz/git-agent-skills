"""Measure skill source bytes/words and optional named-encoding tokens, without model calls.

Named-encoding counts are comparable text measurements, not a claim about a model's
private tokenizer, automatic discovery overhead or total runtime/billing attribution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmark import snapshot, write


def source_metrics(text, encoder=None):
    result = {"utf8_bytes": len(text.encode("utf-8")), "words": len(text.split())}
    if encoder is not None:
        result["encoding_tokens"] = len(encoder.encode(text, disallowed_special=()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--candidate", action="append", required=True)
    parser.add_argument("--encoding", help="Optional tiktoken encoding; dependency is needed only for this measurement")
    args = parser.parse_args()
    encoder = None
    if args.encoding:
        try:
            import tiktoken
            encoder = tiktoken.get_encoding(args.encoding)
        except (ImportError, ValueError) as exc:
            parser.error(str(exc))
    root = args.directory.resolve()
    root.mkdir(parents=True, exist_ok=False)
    results = {}
    for specification in args.candidate:
        label, revision = specification.split("=", 1)
        if not label or Path(label).name != label or label in {".", ".."}:
            parser.error("candidate label must be one directory name")
        destination = root / label
        destination.mkdir()
        snapshot(destination, revision)
        entrypoints = {p.parent.name: source_metrics(p.read_text(encoding="utf-8"), encoder)
                       for p in sorted((destination / "skills").glob("*/SKILL.md"))}
        references = {p.relative_to(destination).as_posix(): source_metrics(p.read_text(encoding="utf-8"), encoder)
                      for p in sorted((destination / "skills").glob("*/references/*.md"))}
        results[label] = {"entrypoints": entrypoints, "conditional_references": references,
                          "entrypoint_totals": {key: sum(row[key] for row in entrypoints.values())
                                                for key in next(iter(entrypoints.values()))}}
    report = {"encoding": args.encoding, "tokenizer_version": tiktoken.__version__ if encoder else None,
              "results": results, "limits": __doc__}
    write(root / "results.json", report)
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
