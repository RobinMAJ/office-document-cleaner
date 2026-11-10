"""The NAS may deny readlink(cwd); kernel socket + UID/argv/birth stay mandatory."""
import errno,hashlib,importlib.util,json,os,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('office_node',Path(__file__).resolve().parents[1]/'deploy/tailscale_node.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Peer:
 def __init__(self,pid):self.pid=pid
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def connect(self,*a):pass
 def getsockopt(self,*a):return struct.pack('3i',self.pid,os.getuid(),0)
class NodeIdentityTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.proc=Path(self.tmp.name)/'proc';self.pid=12345;p=self.proc/str(self.pid);p.mkdir(parents=True)
  (p/'cmdline').write_bytes(b'\0'.join(a.encode() for a in m.ARGS)+b'\0');(p/'stat').write_text('12345 (tailscaled) '+' '.join(['0']*19+['67890']))
  self.record={'pid':self.pid,'start_ticks':'67890','argv_sha256':hashlib.sha256('\0'.join(m.ARGS).encode()).hexdigest(),'cwd':str(m.RELEASE)}
 def tearDown(self):self.tmp.cleanup()
 def run_identity(self,peer=None,denied=True):
  route=lambda value: self.proc if str(value)=='/proc' else Path(value)
  with patch.object(m,'Path',side_effect=route),patch.object(m,'read_private',return_value=self.record),patch.object(m.socket,'socket',return_value=Peer(peer or self.pid)),patch.object(m.socket,'SO_PEERCRED',17,create=True),patch.object(m.os,'readlink',side_effect=PermissionError(errno.EACCES,'Denied') if denied else None,return_value='/unexpected'):
   return m.process_identity()
 def test_denied_cwd_requires_all_other_checks(self):self.assertEqual(self.run_identity(),self.pid)
 def test_wrong_socket_peer_refused(self):
  with self.assertRaisesRegex(RuntimeError,'socket peer'):self.run_identity(peer=999)
 def test_wrong_birth_refused(self):
  self.record['start_ticks']='different'
  with self.assertRaisesRegex(RuntimeError,'identity changed'):self.run_identity()
 def test_readable_foreign_cwd_refused(self):
  with self.assertRaisesRegex(RuntimeError,'working directory'):self.run_identity(denied=False)
if __name__=='__main__':unittest.main()
