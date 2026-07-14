#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 cat=json.loads((ROOT/'skills/catalog.json').read_text()); skills={x['name'] for x in cat['skills']}
 routing=json.loads((ROOT/'tests/routing.json').read_text())['cases']
 scenarios=json.loads((ROOT/'tests/scenarios.json').read_text())['scenarios']
 errors=[]; ids=set(); prompts=set(); pos=Counter(); neg=Counter()
 required_fields={'id','prompt','expected_skill','forbidden_skills','expected_consequence_classes','required_evidence','forbidden_actions'}
 for c in routing:
  missing=required_fields-set(c)
  if missing: errors.append(f"{c.get('id','?')}: missing {sorted(missing)}"); continue
  if c['id'] in ids: errors.append(f"duplicate id {c['id']}")
  ids.add(c['id'])
  normalized=' '.join(c['prompt'].lower().split())
  if normalized in prompts: errors.append(f"duplicate prompt {c['id']}")
  prompts.add(normalized)
  if c['expected_skill'] is not None and c['expected_skill'] not in skills: errors.append(f"{c['id']}: unknown expected skill")
  if c['expected_skill'] is not None and c['expected_skill'] in c['forbidden_skills']: errors.append(f"{c['id']}: expected skill forbidden")
  unknown=set(c['forbidden_skills'])-skills
  if unknown: errors.append(f"{c['id']}: unknown forbidden skills {sorted(unknown)}")
  if c['id'].find('-positive-')>=0 and c['expected_skill'] is not None: pos[c['expected_skill']]+=1
  for f in c['forbidden_skills']: neg[f]+=1
  if not c['expected_consequence_classes'] or not c['required_evidence']: errors.append(f"{c['id']}: empty behavioral metadata")
 for s in skills:
  if pos[s]<3: errors.append(f'{s}: needs >=3 positive cases, has {pos[s]}')
  if neg[s]<2: errors.append(f'{s}: needs >=2 negative/near-miss cases, has {neg[s]}')
 byskill=Counter(x['skill'] for x in scenarios)
 for x in scenarios:
  for field in ('id','skill','kind','setup','expected','forbidden'):
   if field not in x: errors.append(f"scenario {x.get('id','?')}: missing {field}")
  if x.get('skill') not in skills: errors.append(f"scenario {x.get('id','?')}: unknown skill")
 for s in skills:
  if byskill[s]<2: errors.append(f'{s}: needs >=2 scenarios')
 prompts_text=' '.join(c['prompt'] for c in routing)
 if not any('\u0e00'<=ch<='\u0e7f' for ch in prompts_text): errors.append('missing Thai symptom prompt')
 special={(x['skill'],x['kind']) for x in scenarios}
 for pair in [('sync-branches','stale-state'),('edit-commit-history','concurrency'),('migrate-repository','partial-failure'),('configure-git','policy-sensitive'),('manage-large-files','postcondition-failure')]:
  if pair not in special: errors.append(f'missing high-risk scenario {pair}')
 if errors:
  print('FIXTURE EVALUATION FAILED')
  for e in errors: print(f'- {e}')
  return 1
 print(f'PASS: {len(routing)} routing cases; {len(scenarios)} boundary/failure scenarios; positive/negative coverage for {len(skills)} skills')
 return 0
if __name__=='__main__': raise SystemExit(main())
