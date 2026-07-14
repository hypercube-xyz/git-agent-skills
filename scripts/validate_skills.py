#!/usr/bin/env python3
from __future__ import annotations
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REQ=['## Objective','## Use When','## Do Not Use / Route Elsewhere','## Required Evidence','## Decision Rules','## Action Boundaries','## Workflow','## Stop and Reassess','## Verification','## Output Contract','## Reference Trigger']
NAME=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

def frontmatter(text:str):
 if not text.startswith('---\n'): raise ValueError('missing frontmatter')
 end=text.find('\n---\n',4)
 if end<0: raise ValueError('unterminated frontmatter')
 raw=text[4:end].splitlines(); out={}; key=None
 for line in raw:
  if line.startswith('  ') and key:
   out[key]+=' '+line.strip(); continue
  if ':' not in line: raise ValueError(f'invalid frontmatter line: {line}')
  key,val=line.split(':',1);key=key.strip();val=val.strip();out[key]='' if val in {'>-','|','|-'} else val
 return out

def fail(errors,msg): errors.append(msg)
def main():
 errors=[]
 catalog=json.loads((ROOT/'skills/catalog.json').read_text())
 plugin=json.loads((ROOT/'.claude-plugin/plugin.json').read_text())
 names=[x['name'] for x in catalog['skills']]
 dirs=sorted(p.name for p in (ROOT/'skills').iterdir() if p.is_dir())
 if sorted(names)!=dirs: fail(errors,'catalog skill list does not match filesystem')
 if plugin['version']!=catalog['package_version']: fail(errors,'plugin/catalog version mismatch')
 pnames=[Path(x).name for x in plugin['skills']]
 if pnames!=names: fail(errors,'plugin skill order/list differs from catalog')
 tiers=catalog['tiers']; tier_names=[]
 for tier in tiers.values(): tier_names += tier['skills']
 if sorted(tier_names)!=sorted(names) or len(tier_names)!=len(set(tier_names)): fail(errors,'tiers must be disjoint and complete')
 readme=(ROOT/'README.md').read_text()
 for name in names:
  if f'(skills/{name}/SKILL.md)' not in readme: fail(errors,f'{name}: missing README link')
  path=ROOT/'skills'/name/'SKILL.md'; text=path.read_text(); lines=text.splitlines()
  try: fm=frontmatter(text)
  except ValueError as e: fail(errors,f'{name}: {e}'); continue
  if fm.get('name')!=name: fail(errors,f'{name}: frontmatter name mismatch')
  if not NAME.fullmatch(name) or len(name)>64: fail(errors,f'{name}: invalid portable name')
  desc=fm.get('description','').strip()
  if not (1<=len(desc)<=1024): fail(errors,f'{name}: description length {len(desc)}')
  if 'Use ' not in desc and 'Use when' not in desc and 'Use for' not in desc: fail(errors,f'{name}: description lacks activation language')
  for h in REQ:
   if h not in text: fail(errors,f'{name}: missing {h}')
  if len(lines)>500: fail(errors,f'{name}: {len(lines)} lines exceeds heuristic')
  refs=re.findall(r'`(references/[^`]+)`',text)
  if not refs: fail(errors,f'{name}: no direct reference trigger')
  for ref in refs:
   rp=path.parent/ref
   if not rp.is_file(): fail(errors,f'{name}: missing {ref}')
   rtext=rp.read_text()
   if re.search(r'`references/[^`]+`',rtext): fail(errors,f'{name}: reference-to-reference chain in {ref}')
  if 'Activation routes this procedure; it does not authorize' not in text: fail(errors,f'{name}: missing activation/authorization boundary')
  if 'Command completion is evidence only' not in text: fail(errors,f'{name}: missing command-completion discipline')
 # Required package files and high-risk invariants.
 for rel in ['docs/COMPATIBILITY.md','docs/HANDOFF-CONTRACT.md','SECURITY.md','tests/routing.json','tests/scenarios.json','tests/agent-runtime-cases.json','skills/manage-remotes/scripts/inspect_remotes.py']:
  if not (ROOT/rel).is_file(): fail(errors,f'missing {rel}')
 markers={
  'edit-commit-history':['--force-with-lease=refs/heads/<branch>:<exact-fetched-oid>','Query the remote ref after the push'],
  'migrate-repository':['**Discovery:**','**Cutover:**','**Source cleanup:**'],
  'sync-branches':['Immediately before an ordinary push','query the remote ref again'],
  'undo-changes':['git clean -n -- <pathspec>','`-d`, `-x`, `-X`'],
  'manage-large-files':['**Future-only tracking:**','**Published migration:**'],
  'manage-remotes':['refs/tags/*:refs/tags/*'],
  'manage-worktrees':['--porcelain -z'],
 }
 for skill,needles in markers.items():
  t=(ROOT/'skills'/skill/'SKILL.md').read_text()
  for n in needles:
   if n not in t: fail(errors,f'{skill}: missing required revision marker {n}')
 if errors:
  print('VALIDATION FAILED')
  for e in errors: print(f'- {e}')
  return 1
 print(f'PASS: {len(names)} skills; catalogs, frontmatter, references, package files, and high-risk invariants')
 return 0
if __name__=='__main__': raise SystemExit(main())
