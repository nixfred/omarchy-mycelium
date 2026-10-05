"""Read-only check of the seven tested runtime files."""
from pathlib import Path
import hashlib,json

root=Path(__file__).resolve().parents[1]
record=json.loads((root/'tools/runtime-hashes.json').read_text())
assert len(record['files'])==7
for name,digest in record['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,f'Runtime differs: {name}'
digest=hashlib.sha256(''.join(f'{name}\0{value}\n' for name,value in record['files'].items()).encode()).hexdigest()
assert digest==record['sourceTreeSHA256']
print('PASS seven runtime files / sourceTreeSHA256 '+digest)
