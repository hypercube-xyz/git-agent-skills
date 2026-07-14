#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python3 - "$ROOT/skills/catalog.json" <<'PY'
import json,sys
c=json.load(open(sys.argv[1],encoding='utf-8'))
for tier, spec in c['tiers'].items():
    print(f"[{tier}]")
    for name in spec['skills']:
        print(name)
PY
