#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json, os, subprocess, sys, zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
EXCLUDE_NAMES={'.DS_Store','RELEASE-MANIFEST.json'}
EXCLUDE_PREFIXES={'dist','.git'}
VALIDATION=[
 [sys.executable,'scripts/validate_skills.py'],
 [sys.executable,'scripts/smoke_test_git.py'],
]
@dataclass(frozen=True)
class Entry:
    rel: Path; path: Path; mode: int

def run(cmd:list[str])->None:
    proc=subprocess.run(cmd,cwd=ROOT)
    if proc.returncode: raise SystemExit(proc.returncode)

def git(root:Path,*args:str, text:bool=False):
    return subprocess.run(['git','-C',str(root),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=text,check=False)

def require_clean_tracked_state(root:Path=ROOT)->None:
    for args in [('diff','--quiet','--no-ext-diff','--'),('diff','--cached','--quiet','--no-ext-diff','HEAD','--')]:
        proc=git(root,*args)
        if proc.returncode==1: raise SystemExit('release build requires committed tracked files')
        if proc.returncode!=0: raise SystemExit('unable to inspect tracked release state')

def source_revision(root:Path=ROOT)->str:
    proc=git(root,'rev-parse','--verify','HEAD',text=True)
    if proc.returncode!=0: raise SystemExit('unable to resolve release source revision')
    return proc.stdout.strip()

def tracked_files(root:Path=ROOT)->list[Entry]:
    proc=git(root,'ls-files','--cached','--stage','-z')
    if proc.returncode: raise SystemExit('unable to enumerate tracked release files')
    entries=[]
    for record in proc.stdout.split(b'\0'):
        if not record: continue
        try:
            header,raw_path=record.split(b'\t',1); raw_mode,_oid,raw_stage=header.split(b' ',2)
        except ValueError as exc: raise SystemExit('unexpected git ls-files output') from exc
        if raw_stage!=b'0': raise SystemExit('release input contains an unmerged index entry')
        rel=Path(os.fsdecode(raw_path))
        if rel.name in EXCLUDE_NAMES or (rel.parts and rel.parts[0] in EXCLUDE_PREFIXES): continue
        mode=int(raw_mode,8)
        if mode==0o120000: raise SystemExit(f'release input contains a tracked symlink: {rel}')
        if mode not in {0o100644,0o100755}: raise SystemExit(f'unsupported tracked mode {raw_mode.decode()}: {rel}')
        path=root/rel
        if path.is_symlink() or not path.is_file(): raise SystemExit(f'tracked release file is missing or not regular: {rel}')
        entries.append(Entry(rel,path,mode))
    return sorted(entries,key=lambda x:x.rel.as_posix())

def tree_digest(entries:list[Entry])->str:
    d=hashlib.sha256()
    for e in entries:
        d.update(e.rel.as_posix().encode()+b'\0'); d.update(oct(e.mode).encode()+b'\0'); d.update(hashlib.sha256(e.path.read_bytes()).digest())
    return d.hexdigest()

def tool_version(cmd:list[str])->str:
    try: return subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True).stdout.strip()
    except Exception: return 'unavailable'

def archive_time(catalog:dict)->tuple[int,int,int,int,int,int]:
    released=date.fromisoformat(catalog['release_date'])
    if released.year<1980: raise SystemExit('release date is outside ZIP timestamp range')
    return released.year,released.month,released.day,0,0,0

def package_manifest(entries:list[Entry],catalog:dict)->dict[str,object]:
    revision=source_revision()
    return {
      'schema_version':1,
      'package':'git-agent-skills',
      'package_version':catalog['package_version'],
      'release_date':catalog['release_date'],
      'release_tag':f"v{catalog['package_version']}",
      'source_identity':{
        'method':'sha256 over sorted tracked package paths, Git modes, and file content',
        'source_tree_sha256':tree_digest(entries),
        'base_revision':catalog.get('base_release',{}),
        'source_revision':{'kind':'git-commit','commit':revision},
        'upstream_repository':'https://github.com/hypercube-xyz/git-agent-skills'
      },
      'compatibility':catalog['compatibility'],
      'contents':{'skills':len(catalog['skills']),'tracked_files':len(entries)},
    }

def archive_bytes(entries:list[Entry],catalog:dict)->bytes:
    version=catalog['package_version']; prefix=f'git-agent-skills-{version}'
    embedded=(json.dumps(package_manifest(entries,catalog),indent=2,sort_keys=True)+'\n').encode()
    all_entries=[(Path('RELEASE-MANIFEST.json'),0o100644,embedded)]+[(e.rel,e.mode,e.path.read_bytes()) for e in entries]
    names=[r.as_posix() for r,_,_ in all_entries]
    if len(names)!=len(set(names)): raise SystemExit('duplicate archive entries')
    if names.count('RELEASE-MANIFEST.json')!=1: raise SystemExit('release archive must contain exactly one RELEASE-MANIFEST.json')
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_STORED) as z:
        for rel,mode,data in sorted(all_entries,key=lambda x:x[0].as_posix()):
            info=zipfile.ZipInfo(f'{prefix}/{rel.as_posix()}',archive_time(catalog)); info.external_attr=(mode&0xFFFF)<<16; info.create_system=3; info.compress_type=zipfile.ZIP_STORED
            z.writestr(info,data)
    return buf.getvalue()

def release_record(entries,catalog,validation_executed,reproducibility_checked,artifact):
    rec=package_manifest(entries,catalog)
    rec['build_environment']={'python':sys.version.split()[0],'git':tool_version(['git','--version'])}
    rec['validation']={'result':'passed' if validation_executed else 'skipped','commands_executed':[' '.join(c) for c in VALIDATION] if validation_executed else [],'reproducibility_check':'passed' if reproducibility_checked else 'not-run','independent_agent_runtime_comparison':'not run unless supplied by an authorized external runner'}
    rec['artifact']=artifact
    return rec

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--check',action='store_true'); p.add_argument('--skip-validation',action='store_true'); p.add_argument('--output',type=Path); a=p.parse_args()
    catalog=json.loads((ROOT/'skills/catalog.json').read_text())
    if not a.skip_validation:
        for cmd in VALIDATION: run(cmd)
    require_clean_tracked_state(); entries=tracked_files(); first=archive_bytes(entries,catalog)
    if a.check and first!=archive_bytes(entries,catalog): raise SystemExit('release archives are not deterministic')
    version=catalog['package_version']; output=a.output or DIST/f'git-agent-skills-{version}.zip'; output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes(first)
    digest=hashlib.sha256(first).hexdigest(); sha=output.with_suffix(output.suffix+'.sha256'); sha.write_text(f'{digest}  {output.name}\n')
    artifact={'filename':output.name,'sha256':digest,'size_bytes':len(first)}
    sidecar=release_record(entries,catalog,not a.skip_validation,a.check,artifact)
    output.with_suffix('.release.json').write_text(json.dumps(sidecar,indent=2,sort_keys=True)+'\n')
    print(f'PASS: deterministic archive {output}'); print(f'SHA256: {digest}'); return 0
if __name__=='__main__': raise SystemExit(main())
