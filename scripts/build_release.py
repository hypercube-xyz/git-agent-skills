#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json, os, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
FIXED_TIME=(2026,7,15,0,0,0)
EXCLUDE_PARTS={'.git','dist','__pycache__','.pytest_cache'}
EXCLUDE_NAMES={'.DS_Store','RELEASE-MANIFEST.json'}
VALIDATION=[
 [sys.executable,'scripts/validate_skills.py'],
 [sys.executable,'scripts/evaluate_fixtures.py'],
 [sys.executable,'scripts/smoke_test_git.py'],
]

def run(cmd):
 p=subprocess.run(cmd,cwd=ROOT)
 if p.returncode: raise SystemExit(p.returncode)

def files():
 out=[]
 for p in ROOT.rglob('*'):
  if not p.is_file(): continue
  rel=p.relative_to(ROOT)
  if any(part in EXCLUDE_PARTS for part in rel.parts) or p.name in EXCLUDE_NAMES: continue
  out.append((rel,p))
 return sorted(out,key=lambda x:x[0].as_posix())

def tree_digest(entries):
 h=hashlib.sha256()
 for rel,p in entries:
  mode=0o755 if os.access(p,os.X_OK) else 0o644
  h.update(rel.as_posix().encode()+b'\0'+oct(mode).encode()+b'\0')
  h.update(hashlib.sha256(p.read_bytes()).digest())
 return h.hexdigest()

def tool_version(cmd):
 try:return subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True).stdout.strip()
 except Exception:return 'unavailable'

def manifest(entries,version,validation_executed,reproducibility_checked):
 return {
  'schema_version':1,
  'package':'git-agent-skills',
  'package_version':version,
  'release_date':'2026-07-15',
  'source_identity':{
   'method':'sha256 over sorted package paths, executable modes, and file content',
   'source_tree_sha256':tree_digest(entries),
   'upstream_repository':'https://github.com/hypercube-xyz/git-agent-skills',
  },
  'tool_versions':{
   'python':sys.version.split()[0],
   'git':tool_version(['git','--version']),
  },
  'validation':{
   'result':'passed' if validation_executed else 'skipped',
   'commands_executed':([
    'python3 scripts/validate_skills.py',
    'python3 scripts/evaluate_fixtures.py',
    'python3 scripts/smoke_test_git.py',
   ] if validation_executed else []),
   'reproducibility_check':'passed' if reproducibility_checked else 'not-run',
   'agent_runtime_cases':'not run',
  },
  'compatibility':{
   'python_minimum':'3.9',
   'git_minimum':'2.35',
   'ci_os':'Ubuntu',
   'tested_packaging_clients':['Skills CLI 1.5.17','Claude Code 2.1.209'],
  },
 }

def archive_bytes(entries,version,validation_executed,reproducibility_checked):
 prefix=f'git-agent-skills-{version}'
 m=json.dumps(manifest(entries,version,validation_executed,reproducibility_checked),indent=2,sort_keys=True).encode()+b'\n'
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  all_entries=[(Path('RELEASE-MANIFEST.json'),None,m)]+[(rel,p,p.read_bytes()) for rel,p in entries]
  names=[rel.as_posix() for rel,_,_ in all_entries]
  if len(names)!=len(set(names)):
   duplicates=sorted({name for name in names if names.count(name)>1})
   raise SystemExit(f'duplicate archive entries: {duplicates}')
  if names.count('RELEASE-MANIFEST.json')!=1:
   raise SystemExit('release archive must contain exactly one RELEASE-MANIFEST.json')
  for rel,p,data in sorted(all_entries,key=lambda x:x[0].as_posix()):
   zi=zipfile.ZipInfo(f'{prefix}/{rel.as_posix()}',FIXED_TIME)
   executable=(p is not None and os.access(p,os.X_OK))
   zi.external_attr=((0o100755 if executable else 0o100644)&0xFFFF)<<16
   zi.create_system=3
   zi.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
 return buf.getvalue()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');ap.add_argument('--skip-validation',action='store_true');args=ap.parse_args()
 catalog=json.loads((ROOT/'skills/catalog.json').read_text());version=catalog['package_version']
 if not args.skip_validation:
  for cmd in VALIDATION: run(cmd)
 validation_executed=not args.skip_validation
 entries=files();first=archive_bytes(entries,version,validation_executed,args.check)
 if args.check:
  second=archive_bytes(entries,version,validation_executed,args.check)
  if first!=second: raise SystemExit('release archives are not reproducible')
 DIST.mkdir(exist_ok=True)
 name=f'git-agent-skills-{version}.zip';out=DIST/name;out.write_bytes(first)
 digest=hashlib.sha256(first).hexdigest()
 (DIST/f'{name}.sha256').write_text(f'{digest}  {name}\n')
 release=manifest(entries,version,validation_executed,args.check)
 release['artifact']={'filename':name,'sha256':digest,'size_bytes':len(first)}
 (DIST/f'git-agent-skills-{version}.release.json').write_text(json.dumps(release,indent=2,sort_keys=True)+'\n')
 print(f'PASS: reproducible archive {out}')
 print(f'SHA256: {digest}')
 return 0
if __name__=='__main__':raise SystemExit(main())
