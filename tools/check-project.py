"""Check public relative links, SVGs, assets and obvious private host paths."""
from pathlib import Path
import re,xml.etree.ElementTree as ET,subprocess

root=Path(__file__).resolve().parents[1]
files=[root/'README.md',root/'LICENSE',root/'.gitignore']
for folder in ['v4','tests','tools','.github','docs/images']:
    files.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
files.extend(root/'docs'/name for name in ['INSTALL.md','DEVELOPMENT.md','VERIFICATION.md','REQUIREMENTS.md'])
files.append(root/'bridge.py');files.append(root/'manifest.json')
# A durable checkout can retain ignored local-only handoff tools and evidence.
# Scan the exact public Git index there; a standalone publication draft uses
# its own explicit file set before Git initialization.
if (root/'.git').exists():
    files=[root/name for name in subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines()]
for path in files:
    if path.suffix not in ['.png']:
        text=path.read_text()
        assert not re.search(r'/home/[A-Za-z0-9_.-]+/|/run/user/\d{3,}/|HYPRLAND_INSTANCE_SIGNATURE\s*=\s*[\"\'][a-f0-9]{20}',text),f'Private host path: {path.relative_to(root)}'
    if path.suffix=='.svg':ET.fromstring(path.read_text())
for path in [root/'README.md',*[root/'docs'/name for name in ['INSTALL.md','DEVELOPMENT.md','VERIFICATION.md']]]:
    text=path.read_text()
    targets=re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text)+re.findall(r'<img[^>]+src="([^"]+)"',text)
    for target in targets:
        if re.match(r'https?://',target):continue
        name,sep,anchor=target.partition('#');linked=(path.parent/name) if name else path
        assert linked.is_file(),f'Broken link in {path.name}: {target}'
        if anchor:
            headings=re.findall(r'^#+\s+(.+)$',linked.read_text(),re.M)
            slugs=[re.sub(r'[^\w -]','',h.lower()).replace(' ','-') for h in headings]
            assert anchor in slugs,f'Broken anchor: {target}'
assert len(list((root/'docs/images').glob('*.png')))==4
print('PASS public relative links, SVG markup, native assets and private-path scan')
