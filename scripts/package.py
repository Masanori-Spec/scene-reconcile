from pathlib import Path
import hashlib, json, zipfile
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / 'scene-reconcile-output'
EXCLUDED = {'node_modules', '.git', '__pycache__', 'test-results', 'native-run'}
files=[]
for path in sorted(ROOT.rglob('*')):
    if not path.is_file() or path.is_symlink() or set(path.relative_to(ROOT).parts)&EXCLUDED or path.suffix=='.pyc':continue
    name=path.relative_to(ROOT).as_posix()
    files.append((name,path))
OUT.mkdir(exist_ok=True)
manifest={'format':'SceneReconcile source manifest','files':[{'path':name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for name,path in files]}
manifest_bytes=(json.dumps(manifest,indent=2)+'\n').encode()
(OUT/'source-manifest.json').write_bytes(manifest_bytes)
archive=OUT/'scene-reconcile.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,path in files:z.writestr('scene-reconcile/'+name,path.read_bytes())
    z.writestr('scene-reconcile/SOURCE-MANIFEST.json',manifest_bytes)
with zipfile.ZipFile(archive) as z:
    for entry in manifest['files']:
        assert hashlib.sha256(z.read('scene-reconcile/'+entry['path'])).hexdigest()==entry['sha256']
report={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'fileCount':len(files),'allEntriesMatch':True}
(OUT/'package-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
