#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, os, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class TestFailure(RuntimeError): pass

def run(*args, cwd=None, check=True, env=None, text=True):
    proc=subprocess.run([str(a) for a in args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=text,env=env)
    if check and proc.returncode:
        raise TestFailure(f"command failed ({proc.returncode}): {' '.join(map(str,args))}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc

def init(path:Path, bare=False):
    path.mkdir(parents=True,exist_ok=True)
    run('git','init','--bare' if bare else '--initial-branch=main',path)
    if bare:
        run('git','symbolic-ref','HEAD','refs/heads/main',cwd=path)
    if not bare:
        run('git','config','user.name','Test User',cwd=path);run('git','config','user.email','test@example.invalid',cwd=path)

def commit(repo:Path,name='file.txt',content='one\n',message='commit'):
    p=repo/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
    run('git','add','--',name,cwd=repo);run('git','commit','-m',message,cwd=repo)
    return run('git','rev-parse','HEAD',cwd=repo).stdout.strip()

def clone(src:Path,dst:Path):
    run('git','clone',str(src),str(dst));run('git','config','user.name','Test User',cwd=dst);run('git','config','user.email','test@example.invalid',cwd=dst)

def assert_(cond,msg):
    if not cond: raise TestFailure(msg)

def t_remote_helper_redaction(tmp):
    repo=tmp/'repo';init(repo)
    run('git','remote','add','origin','https://user:token@example.com/team/repo.git?secret=yes',cwd=repo)
    p=run(sys.executable,ROOT/'skills/manage-remotes/scripts/inspect_remotes.py',repo).stdout
    assert_('token' not in p and 'secret=yes' not in p and '<redacted-user>@example.com' in p,'credential redaction failed')
    data=json.loads(p);e=data['remotes']['origin']['url'][0]
    assert_(e['scope']=='local' and 'config' in e['origin'],'scope/origin missing')

def t_remote_helper_opaque(tmp):
    repo=tmp/'repo';init(repo);run('git','remote','add','opaque','helper::credential-payload',cwd=repo)
    p=run(sys.executable,ROOT/'skills/manage-remotes/scripts/inspect_remotes.py',repo).stdout
    assert_('credential-payload' not in p and '<redacted-opaque>' in p,'opaque value echoed')

def t_remote_helper_names_with_separators(tmp):
    repo=tmp/'repo';init(repo)
    run('git','remote','add','team.prod','https://example.com/team/prod.git',cwd=repo)
    run('git','remote','add','team/prod','https://example.com/team/slash.git',cwd=repo)
    data=json.loads(run(sys.executable,ROOT/'skills/manage-remotes/scripts/inspect_remotes.py',repo).stdout)
    assert_('team.prod' in data['remotes'] and 'team/prod' in data['remotes'],'remote names with dot/slash were lost')

def t_force_with_lease_rejects_stale(tmp):
    bare=tmp/'remote.git';init(bare,True)
    seed=tmp/'seed';init(seed);old=commit(seed);run('git','remote','add','origin',bare,cwd=seed);run('git','push','-u','origin','main',cwd=seed)
    a=tmp/'a';b=tmp/'b';clone(bare,a);clone(bare,b)
    expected=run('git','rev-parse','origin/main',cwd=a).stdout.strip()
    commit(b,'b.txt','b\n','concurrent');run('git','push','origin','main',cwd=b)
    commit(a,'a.txt','a\n','rewrite candidate')
    p=run('git','push','origin','HEAD:refs/heads/main',f'--force-with-lease=refs/heads/main:{expected}',cwd=a,check=False)
    assert_(p.returncode!=0,'stale exact lease unexpectedly succeeded')
    remote=run('git','ls-remote',bare,'refs/heads/main').stdout.split()[0]
    assert_(remote!=expected and remote!=run('git','rev-parse','HEAD',cwd=a).stdout.strip(),'remote state wrong')

def t_normal_push_remote_query(tmp):
    bare=tmp/'r.git';init(bare,True);repo=tmp/'repo';init(repo);oid=commit(repo);run('git','remote','add','origin',bare,cwd=repo);run('git','push','origin','main',cwd=repo)
    observed=run('git','ls-remote','origin','refs/heads/main',cwd=repo).stdout.split()[0]
    assert_(observed==oid,'post-push remote query mismatch')

def t_tag_objects(tmp):
    repo=tmp/'repo';init(repo);oid=commit(repo)
    run('git','tag','light',oid,cwd=repo);run('git','tag','-a','annotated','-m','release',oid,cwd=repo)
    assert_(run('git','cat-file','-t','light',cwd=repo).stdout.strip()=='commit','lightweight tag type')
    assert_(run('git','cat-file','-t','annotated',cwd=repo).stdout.strip()=='tag','annotated tag type')
    assert_(run('git','rev-parse','annotated^{}',cwd=repo).stdout.strip()==oid,'peeled target mismatch')

def t_tag_exact_lease_rejects_stale_move_and_delete(tmp):
    bare=tmp/'r.git';init(bare,True);seed=tmp/'seed';init(seed);commit(seed);run('git','tag','release',cwd=seed);run('git','remote','add','origin',bare,cwd=seed);run('git','push','origin','main','refs/tags/release',cwd=seed)
    a=tmp/'a';b=tmp/'b';clone(bare,a);clone(bare,b);run('git','fetch','origin','refs/tags/release:refs/tags/release',cwd=a);run('git','fetch','origin','refs/tags/release:refs/tags/release',cwd=b)
    expected=run('git','ls-remote','origin','refs/tags/release',cwd=a).stdout.split()[0]
    concurrent=commit(b,'concurrent.txt','new\n','new tag target');run('git','tag','-f','release',concurrent,cwd=b);run('git','push','--force','origin','refs/tags/release:refs/tags/release',cwd=b)
    replacement=commit(a,'replacement.txt','candidate\n','candidate tag target');run('git','tag','-f','release',replacement,cwd=a)
    move=run('git','push','origin','refs/tags/release:refs/tags/release',f'--force-with-lease=refs/tags/release:{expected}',cwd=a,check=False)
    delete=run('git','push','origin',':refs/tags/release',f'--force-with-lease=refs/tags/release:{expected}',cwd=a,check=False)
    observed=run('git','ls-remote','origin','refs/tags/release',cwd=a).stdout.split()[0]
    assert_(move.returncode!=0 and delete.returncode!=0 and observed==concurrent,'stale tag lease did not protect concurrent remote state')

def t_worktree_porcelain_z(tmp):
    repo=tmp/'repo';init(repo);commit(repo);run('git','branch','feature',cwd=repo)
    path=tmp/'wt with space';run('git','worktree','add',path,'feature',cwd=repo)
    raw=run('git','worktree','list','--porcelain','-z',cwd=repo,text=False).stdout
    assert_(b'\0' in raw and str(path).encode() in raw,'porcelain -z missing path or NUL')

def t_worktree_branch_delete_blocked(tmp):
    repo=tmp/'repo';init(repo);commit(repo);run('git','branch','feature',cwd=repo);wt=tmp/'wt';run('git','worktree','add',wt,'feature',cwd=repo)
    p=run('git','branch','-D','feature',cwd=repo,check=False)
    assert_(p.returncode!=0,'deleted branch checked out in linked worktree')

def t_clean_preview_pathological(tmp):
    repo=tmp/'repo';init(repo);commit(repo)
    names=['-cache','line\nbreak.tmp','keep.txt']
    for n in names:(repo/n).write_text('x')
    raw=run('git','status','--porcelain=v1','-z','--untracked-files=all',cwd=repo,text=False).stdout
    assert_(b'-cache' in raw and b'line\nbreak.tmp' in raw,'NUL inventory lost names')
    preview=run('git','clean','-n','--','-cache',cwd=repo).stdout
    assert_('-cache' in preview and (repo/'-cache').exists(),'clean preview incorrect')
    run('git','clean','-f','--','-cache',cwd=repo)
    assert_(not (repo/'-cache').exists() and (repo/'line\nbreak.tmp').exists() and (repo/'keep.txt').exists(),'exact clean changed protected files')

def t_reset_hard_preserves_non_obstructing_untracked(tmp):
    repo=tmp/'repo';init(repo);commit(repo,content='base\n');(repo/'file.txt').write_text('changed\n');(repo/'untracked').write_text('keep')
    run('git','reset','--hard','HEAD',cwd=repo)
    assert_((repo/'file.txt').read_text()=='base\n' and (repo/'untracked').exists(),'non-obstructing untracked path should survive')


def t_reset_hard_removes_untracked_obstruction(tmp):
    repo=tmp/'repo';init(repo);base=commit(repo)
    (repo/'obstacle').write_text('tracked target\n');run('git','add','--','obstacle',cwd=repo);run('git','commit','-m','add obstacle',cwd=repo)
    target=run('git','rev-parse','HEAD',cwd=repo).stdout.strip();run('git','reset','--hard',base,cwd=repo)
    (repo/'obstacle').mkdir();(repo/'obstacle'/'unique.txt').write_text('untracked\n')
    run('git','reset','--hard',target,cwd=repo)
    assert_((repo/'obstacle').is_file() and not (repo/'obstacle'/'unique.txt').exists(),'obstructing untracked directory was not replaced as documented')

def t_unstage_preserves_worktree(tmp):
    repo=tmp/'repo';init(repo);commit(repo);(repo/'file.txt').write_text('edited\n');run('git','add','--','file.txt',cwd=repo);run('git','restore','--staged','--','file.txt',cwd=repo)
    assert_((repo/'file.txt').read_text()=='edited\n','worktree edit lost');assert_(run('git','diff','--cached','--quiet',cwd=repo,check=False).returncode==0,'index still staged')

def t_reflog_recovery(tmp):
    repo=tmp/'repo';init(repo);base=commit(repo);lost=commit(repo,'lost.txt','valuable\n','lost');run('git','reset','--hard',base,cwd=repo)
    run('git','branch','recovered',lost,cwd=repo);assert_(run('git','show','recovered:lost.txt',cwd=repo).stdout=='valuable\n','recovery ref failed')

def t_conflict_stages_and_abort(tmp):
    repo=tmp/'repo';init(repo);commit(repo,content='base\n');run('git','checkout','-b','side',cwd=repo);commit(repo,content='side\n',message='side');run('git','checkout','main',cwd=repo);commit(repo,content='main\n',message='main')
    p=run('git','merge','side',cwd=repo,check=False);assert_(p.returncode!=0,'expected conflict')
    stages=run('git','ls-files','-u',cwd=repo).stdout;assert_('\tfile.txt' in stages,'conflict stages missing');run('git','merge','--abort',cwd=repo);assert_((repo/'file.txt').read_text()=='main\n','abort did not restore')

def t_tag_prune_dry_run_shared_namespace(tmp):
    bare=tmp/'r.git';init(bare,True);seed=tmp/'seed';init(seed);commit(seed);run('git','tag','remote-tag',cwd=seed);run('git','remote','add','origin',bare,cwd=seed);run('git','push','origin','main','refs/tags/remote-tag',cwd=seed)
    repo=tmp/'repo';clone(bare,repo);run('git','tag','local-only',cwd=repo);run('git','config','--unset-all','remote.origin.fetch',cwd=repo);run('git','config','--add','remote.origin.fetch','+refs/heads/*:refs/remotes/origin/*',cwd=repo);run('git','config','--add','remote.origin.fetch','+refs/tags/*:refs/tags/*',cwd=repo)
    p=run('git','fetch','--prune','--dry-run','origin',cwd=repo)
    combined=p.stdout+p.stderr
    assert_('local-only' in combined,'dry-run did not expose shared-namespace prune candidate')
    assert_(run('git','rev-parse','refs/tags/local-only',cwd=repo).returncode==0,'dry-run mutated tag')

def t_atomic_multiref_push(tmp):
    bare=tmp/'r.git';init(bare,True);repo=tmp/'repo';init(repo);commit(repo);run('git','branch','a',cwd=repo);run('git','branch','b',cwd=repo);run('git','remote','add','origin',bare,cwd=repo)
    run('git','push','--atomic','origin','refs/heads/a','refs/heads/b',cwd=repo)
    out=run('git','ls-remote','origin','refs/heads/a','refs/heads/b',cwd=repo).stdout;assert_(out.count('\n')==2,'atomic multi-ref push incomplete')

def t_submodule_gitlink(tmp):
    sub=tmp/'sub';init(sub);soid=commit(sub,'sub.txt','sub\n')
    parent=tmp/'parent';init(parent);commit(parent)
    env=os.environ.copy();env['GIT_ALLOW_PROTOCOL']='file'
    run('git','-c','protocol.file.allow=always','submodule','add',sub,'deps/sub',cwd=parent,env=env);run('git','commit','-am','add submodule',cwd=parent)
    mode_oid=run('git','ls-files','-s','deps/sub',cwd=parent).stdout.split()
    assert_(mode_oid[0]=='160000' and mode_oid[1]==soid,'gitlink mode/OID mismatch')

def t_pickaxe(tmp):
    repo=tmp/'repo';init(repo);commit(repo,content='base\n');target=commit(repo,content='base\nneedle\n',message='add needle')
    out=run('git','log','-Sneedle','--format=%H','--','file.txt',cwd=repo).stdout.strip().splitlines();assert_(target in out,'pickaxe missed commit')

def t_bisect_boundary(tmp):
    repo=tmp/'repo';init(repo)
    first=commit(repo,content='0\n',message='good');commit(repo,content='1\n',message='good2');bad=commit(repo,content='BAD\n',message='bad');commit(repo,content='BAD2\n',message='bad2')
    script=tmp/'oracle.sh';script.write_text('#!/bin/sh\nif grep -q BAD file.txt; then exit 1; fi\nexit 0\n');script.chmod(0o755)
    run('git','bisect','start','HEAD',first,cwd=repo);run('git','bisect','run',script,cwd=repo)
    observed=run('git','rev-parse','refs/bisect/bad',cwd=repo).stdout.strip()
    assert_(observed==bad,'bisect identified the wrong first-bad commit');run('git','bisect','reset',cwd=repo)

def t_installer_preflight_no_partial(tmp):
    target=tmp/'skills';target.mkdir();names=json.loads((ROOT/'skills/catalog.json').read_text())['skills'];last=target/names[-1]['name'];last.mkdir()
    p=run(sys.executable,ROOT/'scripts/link_skills.py','--target',target,cwd=ROOT,check=False)
    assert_(p.returncode!=0,'preflight should fail')
    created=[x for x in target.iterdir() if x.is_symlink()]
    assert_(not created,'installer partially mutated before conflict')

def t_installer_dry_run(tmp):
    target=tmp/'skills';p=run(sys.executable,ROOT/'scripts/link_skills.py','--target',target,'--dry-run',cwd=ROOT)
    assert_('WOULD LINK' in p.stdout and not target.exists(),'dry-run mutated target')

def t_installer_restores_foreign_symlink_on_mid_item_failure(tmp):
    target=tmp/'skills';target.mkdir();catalog=json.loads((ROOT/'skills/catalog.json').read_text())['skills'];name=catalog[0]['name']
    old_target=tmp/'old-skill';old_target.mkdir();dest=target/name;dest.symlink_to(old_target,target_is_directory=True)
    spec=importlib.util.spec_from_file_location('link_skills_test',ROOT/'scripts/link_skills.py');module=importlib.util.module_from_spec(spec);assert_(spec.loader is not None,'loader unavailable');spec.loader.exec_module(module)
    original=Path.symlink_to
    def failing_symlink(self,target_value,*args,**kwargs):
        if self==dest and Path(target_value).resolve(strict=False)!=(old_target.resolve(strict=False)):
            raise OSError('injected replacement failure')
        return original(self,target_value,*args,**kwargs)
    old_argv=sys.argv[:];Path.symlink_to=failing_symlink
    try:
        sys.argv=['link_skills.py','--target',str(target),'--force-symlinks'];rc=module.main()
    finally:
        Path.symlink_to=original;sys.argv=old_argv
    assert_(rc==3 and dest.is_symlink() and (dest.parent/os.readlink(dest)).resolve(strict=False)==old_target.resolve(),'foreign symlink was not restored')


def t_release_manifest_marks_skipped_validation(tmp):
    p=run(sys.executable,ROOT/'scripts/build_release.py','--check','--skip-validation',cwd=ROOT)
    archive=ROOT/'dist/git-agent-skills-1.0.0.zip'
    with zipfile.ZipFile(archive) as z:
        manifest=json.loads(z.read('git-agent-skills-1.0.0/RELEASE-MANIFEST.json'))
    validation=manifest['validation']
    assert_(validation['result']=='skipped' and validation['commands_executed']==[] and validation['reproducibility_check']=='passed','skipped validation was reported as passed')

def t_frontmatter_no_mutation_claim(tmp):
    # Mechanical package invariant included in smoke suite for a stable count.
    for p in (ROOT/'skills').glob('*/SKILL.md'):
        t=p.read_text();assert_('Activation routes this procedure; it does not authorize' in t,f'{p} lacks boundary')

TESTS=[
 t_remote_helper_redaction,t_remote_helper_opaque,t_remote_helper_names_with_separators,
 t_force_with_lease_rejects_stale,t_normal_push_remote_query,t_tag_objects,t_tag_exact_lease_rejects_stale_move_and_delete,
 t_worktree_porcelain_z,t_worktree_branch_delete_blocked,t_clean_preview_pathological,
 t_reset_hard_preserves_non_obstructing_untracked,t_reset_hard_removes_untracked_obstruction,
 t_unstage_preserves_worktree,t_reflog_recovery,t_conflict_stages_and_abort,t_tag_prune_dry_run_shared_namespace,
 t_atomic_multiref_push,t_submodule_gitlink,t_pickaxe,t_bisect_boundary,t_installer_preflight_no_partial,
 t_installer_dry_run,t_installer_restores_foreign_symlink_on_mid_item_failure,
 t_release_manifest_marks_skipped_validation,t_frontmatter_no_mutation_claim]

def main():
    failures=[]
    with tempfile.TemporaryDirectory(prefix='git-skill-smoke-') as d:
        base=Path(d)
        for test in TESTS:
            td=base/test.__name__;td.mkdir()
            try:test(td);print(f'PASS: {test.__name__}')
            except Exception as e:failures.append((test.__name__,str(e)));print(f'FAIL: {test.__name__}: {e}')
    if failures:
        print(f'{len(failures)} failures',file=sys.stderr);return 1
    print(f'PASS: {len(TESTS)} local Git/package semantic smoke tests');return 0
if __name__=='__main__':raise SystemExit(main())
