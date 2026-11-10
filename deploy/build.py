"""Validate the standalone release and build its public-file allowlist."""
from pathlib import Path
import hashlib,json,re,sys
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
class Audit(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.assets=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if a.get('id'):self.ids.append(a['id'])
  if tag=='script':
   assert a.get('src'), 'Inline scripts are not allowed by the deployed CSP'
   self.assets.append(a['src'])
  if tag=='link' and a.get('rel')=='stylesheet':self.assets.append(a['href'])
  assert not any(k.startswith('on') or k=='style' for k in a), 'Inline handlers/styles are not allowed'
def build():
 site=ROOT/'site';html=(site/'index.html').read_text();a=Audit();a.feed(html)
 assert len(a.ids)==len(set(a.ids))
 for asset in a.assets:
  assert not asset.startswith(('http:','https:','//','/')) and (site/asset).is_file(),asset
 js=(site/'assets/app.js').read_text()
 assert not any(x in js for x in ('window.claude','claude.ai','XMLHttpRequest','fetch(','sendBeacon'))
 pub={str(p.relative_to(site)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(site.rglob('*')) if p.is_file()}
 scripts={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'deploy').glob('*.py'))}
 manifest={'schema':'office-document-cleaner-v1','version':'20261110-v1','mode':'browser-only','uploads':False,'authentication':False,'public_files':pub,'deployment_files':scripts}
 (ROOT/'MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'public_files':len(pub),'dom_ids':len(a.ids),'manifest_sha256':hashlib.sha256((ROOT/'MANIFEST.json').read_bytes()).hexdigest()}))
if __name__=='__main__':build()
