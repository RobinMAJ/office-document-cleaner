import hashlib,importlib.util,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
spec=importlib.util.spec_from_file_location('office_static',Path(__file__).resolve().parents[1]/'deploy/static_server.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class StaticBoundaryTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.site=self.root/'site';self.site.mkdir();(self.site/'index.html').write_text('<title>Office</title>');(self.root/'private.env').write_text('synthetic secret')
  self.files={'index.html':hashlib.sha256((self.site/'index.html').read_bytes()).hexdigest()};(self.root/'MANIFEST.json').write_text(json.dumps({'public_files':self.files}));module.RELEASE=self.root;module.DIST=self.site
  self.server=ThreadingHTTPServer(('127.0.0.1',0),module.handler_type(module.load_public_files()));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.base='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):self.server.shutdown();self.server.server_close();self.temp.cleanup()
 def request(self,path='/',method='GET',data=None):
  try:return urllib.request.urlopen(urllib.request.Request(self.base+path,method=method,data=data),timeout=2)
  except urllib.error.HTTPError as e:return e
 def test_public_page_and_privacy_headers(self):
  with self.request() as r:
   self.assertEqual(r.status,200);self.assertIn(b'Office',r.read());self.assertIn("connect-src 'none'",r.headers['Content-Security-Policy']);self.assertEqual(r.headers['X-Frame-Options'],'DENY')
 def test_head(self):
  with self.request(method='HEAD') as r:self.assertEqual(r.status,200);self.assertEqual(r.read(),b'')
 def test_private_routes_and_traversal(self):
  for p in ('/.git/config','/.env','/MANIFEST.json','/README.md','/../private.env','/%2e%2e/private.env','/api/upload','/site/index.html','/assets/'):
   with self.subTest(path=p):
    with self.request(p) as r:self.assertEqual(r.status,404)
 def test_no_upload_or_mutation(self):
  for method in ('POST','PUT','PATCH','DELETE','OPTIONS'):
   with self.subTest(method=method):
    with self.request(method=method,data=b'not a document') as r:self.assertEqual(r.status,405)
 def test_tampered_asset_refused(self):
  (self.site/'index.html').write_text('tampered')
  with self.request() as r:self.assertEqual(r.status,503)
 def test_manifest_rejects_unexpected_file(self):
  (self.site/'accidental.py').write_text('test')
  with self.assertRaises(RuntimeError):module.load_public_files()
if __name__=='__main__':unittest.main()
