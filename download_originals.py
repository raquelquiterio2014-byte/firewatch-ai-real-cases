"""Explicit restoration of the three public, hash-pinned original map PDFs."""
import hashlib
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent

def restore(item):
    name=item['name'];parsed=urlsplit(item['url'])
    if not re.fullmatch(r'EMSR592_[A-Za-z0-9_]+\.pdf',name) or not re.fullmatch(r'[a-f0-9]{64}',item['sha256']):
        raise ValueError('Invalid original-file manifest')
    if parsed.scheme!='https' or parsed.netloc!='cems-mapping-website.s3.eu-west-1.amazonaws.com' or not parsed.path.startswith('/static/activations/EMSR592/'):
        raise ValueError('Unexpected original-file provider')
    target=ROOT/'originals'/name
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==item['sha256']:
        return name+' — already verified'
    with urlopen(item['url'],timeout=30) as response:
        data=response.read(25_000_001)
    if len(data)>25_000_000 or len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
        raise ValueError('Original file size/hash mismatch: '+name)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        target.rename(target.with_name(name+'.unverified-'+uuid.uuid4().hex[:8]+'.bak'))
    target.write_bytes(data)
    return name+' — downloaded and verified'

def main():
    items=json.loads((ROOT/'originals/download_manifest.json').read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(restore,items):print(result)

if __name__=='__main__':main()
