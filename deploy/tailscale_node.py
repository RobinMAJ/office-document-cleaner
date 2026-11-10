"""Project-specific NAS node. No old-node mutation or imported node identity."""
import argparse,errno,hashlib,json,os,socket,stat,struct,subprocess,time
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path('/config/workspace/office-document-cleaner')
RELEASE=Path(__file__).resolve().parents[1]
BIN=Path('/config/workspace/project_AI4oribital_A1/deployment/llm-20260920-v1/network-bin')
STATE=ROOT/'var/tailscale';SOCKET=Path('/tmp/office-document-cleaner.sock');HOST='office-document-cleaner.tailee7aa5.ts.net';PORT=41660
HASHES={'tailscale':'f10a8875d7d673501bc73b0aee686c8bdf4b0dd7dcc381f5790c94b8991c7385','tailscaled':'14a65e655d27a28c60020de742105169541f56f91a704b4e1ac43e3aa8323299'}
ARGS=[str(BIN/'tailscaled'),'--tun=userspace-networking','--statedir='+str(STATE),'--state='+str(STATE/'tailscaled.state'),'--socket='+str(SOCKET),'--port='+str(PORT)]
OLD={
 '/tmp/a1-llm-tailscale.sock':('jiabin-a11.tailee7aa5.ts.net','nhHVMn4E2r11CNTRL'),
 '/tmp/jiabino11-orbital.sock':('jiabino11.tailee7aa5.ts.net','nzhMabwCSq11CNTRL'),
 '/tmp/jiabin-chili.sock':('jiabin-chili.tailee7aa5.ts.net','nxFdcA6pe721CNTRL')}
def no_symlinks(path):
 if not path.is_absolute() or str(path)!=os.path.normpath(str(path)):raise RuntimeError('Noncanonical path')
 if any(p.is_symlink() for p in (path,*path.parents)):raise RuntimeError('Symlinked path refused')
def private_json(path,value):
 no_symlinks(path);tmp=path.with_name(path.name+'.'+str(os.getpid())+'.incoming')
 fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(str(tmp),str(path))
def read_private(path):
 no_symlinks(path);s=path.stat()
 if s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600:raise RuntimeError('Private state identity changed')
 return json.loads(path.read_text())
def command(sock,args,timeout=15):
 return subprocess.run([str(BIN/'tailscale'),'--socket='+str(sock),*args],capture_output=True,text=True,timeout=timeout)
def read_json(sock,args):
 p=command(sock,args)
 if p.returncode:raise RuntimeError('Tailscale query failed for '+str(sock))
 return json.loads(p.stdout)
def legacy_snapshot():
 out={}
 for sock,(host,node_id) in OLD.items():
  d=read_json(sock,['status','--json']);me=d.get('Self',{})
  if d.get('BackendState')!='Running' or me.get('DNSName','').rstrip('.')!=host or me.get('ID')!=node_id:raise RuntimeError('Existing platform identity changed: '+host)
  out[sock]={'dns':host,'node_id':node_id,'serve':read_json(sock,['serve','status','--json']),'funnel':read_json(sock,['funnel','status','--json'])}
 return out
def verify():
 if os.getuid()==0 or RELEASE.parent!=ROOT/'deployment':raise RuntimeError('Run as NAS project owner from its own versioned release')
 for p in (ROOT,RELEASE):
  no_symlinks(p)
  if p.stat().st_uid!=os.getuid() or not p.is_dir():raise RuntimeError('Unexpected owner')
 manifest=json.loads((RELEASE/'MANIFEST.json').read_text())
 for name,expected in manifest['deployment_files'].items():
  p=RELEASE/name;no_symlinks(p)
  if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise RuntimeError('Reviewed deployment source changed')
 for name,expected in HASHES.items():
  p=BIN/name;no_symlinks(p)
  if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise RuntimeError('Pinned official Tailscale binary changed')
def ticks(pid):return (Path('/proc')/str(pid)/'stat').read_text().rpartition(')')[2].split()[19]
def process_identity():
 record=read_private(STATE/'daemon.json');pid=record['pid'];proc=Path('/proc')/str(pid)
 if record.get('argv_sha256')!=hashlib.sha256('\0'.join(ARGS).encode()).hexdigest() or record.get('cwd')!=str(RELEASE):raise RuntimeError('Private launcher provenance changed')
 try:
  if proc.stat().st_uid!=os.getuid() or (proc/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')!=[x.encode() for x in ARGS] or ticks(pid)!=record['start_ticks']:raise RuntimeError('Node process identity changed')
 except FileNotFoundError:raise RuntimeError('Recorded node stopped; preserve state and review before recovery')
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
  peer.connect(str(SOCKET));pid2,uid,_=struct.unpack('3i',peer.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
 if (pid2,uid)!=(pid,os.getuid()):raise RuntimeError('Node socket peer changed')
 try:
  if Path(os.readlink(proc/'cwd'))!=RELEASE:raise RuntimeError('Node working directory changed')
 except OSError as e:
  if e.errno not in (errno.EACCES,errno.EPERM):raise
 return pid
def ensure_state():
 no_symlinks(STATE)
 if STATE.exists():
  if STATE.stat().st_uid!=os.getuid() or stat.S_IMODE(STATE.stat().st_mode)!=0o700:raise RuntimeError('Untrusted node state directory')
  if read_private(STATE/'purpose.json')!={'host':HOST,'project':'office-document-cleaner'}:raise RuntimeError('Foreign node state')
 else:
  STATE.mkdir(parents=True,mode=0o700);os.chmod(str(STATE),0o700);private_json(STATE/'purpose.json',{'host':HOST,'project':'office-document-cleaner'})
def start():
 ensure_state()
 if (STATE/'daemon.json').exists():return process_identity()
 if SOCKET.exists() or SOCKET.is_symlink():raise RuntimeError('Foreign socket exists; nothing removed')
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:s.bind(('0.0.0.0',PORT))
 fd=os.open(str(STATE/'daemon.log'),os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'ab') as log:p=subprocess.Popen(ARGS,cwd=str(RELEASE),stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,env={**os.environ,'TS_NO_LOGS_NO_SUPPORT':'true'})
 for _ in range(60):
  if p.poll() is not None:raise RuntimeError('New node exited')
  if SOCKET.exists():
   info=SOCKET.stat()
   if not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.getuid():raise RuntimeError('Unexpected new socket identity')
   os.chmod(str(SOCKET),0o600)
   try:read_json(SOCKET,['status','--json'])
   except (RuntimeError,ValueError,subprocess.TimeoutExpired):
    time.sleep(.2);continue
   private_json(STATE/'daemon.json',{'pid':p.pid,'argv_sha256':hashlib.sha256('\0'.join(ARGS).encode()).hexdigest(),'start_ticks':ticks(p.pid),'cwd':str(RELEASE)})
   process_identity();return p.pid
  time.sleep(.2)
 raise RuntimeError('New node readiness timed out')
def own_status():
 d=read_json(SOCKET,['status','--json'])
 if d.get('BackendState')=='Running' and d.get('Self',{}).get('DNSName','').rstrip('.')!=HOST:raise RuntimeError('Wrong new-node DNS name; do not publish')
 return d
def main():
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['probe','start','enroll','status','publish','pause']);mode=a.parse_args().mode
 os.umask(0o077);verify();before=legacy_snapshot()
 if mode=='probe':
  print(json.dumps({'old_nodes_preserved':True,'new_host':HOST,'new_state_exists':STATE.exists(),'new_socket_exists':SOCKET.exists(),'public_route_enabled_by_this_script':False}));return
 pid=start() if mode in ('start','enroll') else process_identity()
 d=own_status()
 if mode=='enroll' and d.get('BackendState')!='Running':
  command(SOCKET,['up','--hostname=office-document-cleaner','--accept-dns=false','--accept-routes=false','--ssh=false','--advertise-routes=','--advertise-exit-node=false','--timeout=5s'],timeout=15);d=own_status()
 if mode in ('publish','pause'):
  if d.get('BackendState')!='Running' or HOST not in (d.get('CertDomains') or []):raise RuntimeError('Owner enrollment / exact HTTPS identity not ready')
  if mode=='publish':
   import urllib.request
   with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:18815/',timeout=3) as r:
    if r.status!=200 or b'Office Cleaner' not in r.read():raise RuntimeError('Static origin not ready')
   expected={'TCP':{'443':{'HTTPS':True}},'Web':{HOST+':443':{'Handlers':{'/':{'Proxy':'http://127.0.0.1:18815'}}}},'AllowFunnel':{HOST+':443':True}}
   current=read_json(SOCKET,['serve','status','--json'])
   if current and current!=expected:raise RuntimeError('Unexpected new-node route; no overwrite')
   if not current:
    r=command(SOCKET,['funnel','--bg','--https=443','http://127.0.0.1:18815'],timeout=30)
    if r.returncode:
     print(r.stdout[-2500:]);print(r.stderr[-1500:]);raise RuntimeError('Funnel requires owner permission review')
   if read_json(SOCKET,['funnel','status','--json'])!=expected:raise RuntimeError('Unexpected public route after activation')
  else:
   r=command(SOCKET,['funnel','--https=443','off'])
   if r.returncode:raise RuntimeError('New-node pause failed')
 if legacy_snapshot()!=before:raise RuntimeError('Existing platform routing changed; no old-node repair attempted')
 receipt={'pid':pid,'state':d.get('BackendState'),'dns':d.get('Self',{}).get('DNSName','').rstrip('.'),'node_id':d.get('Self',{}).get('ID'),'old_nodes_preserved':True,'authentication':False,'uploads':False,'mode':mode}
 if d.get('BackendState')=='Running':receipt['funnel']=read_json(SOCKET,['funnel','status','--json'])
 private_json(STATE/'status.json',receipt)
 url=d.get('AuthURL','')
 if mode=='enroll' and url:
  if urlparse(url).scheme!='https' or urlparse(url).hostname!='login.tailscale.com':raise RuntimeError('Unexpected enrollment host')
  receipt['owner_authorization_url']=url # stdout only, never added to source or status receipt
 print(json.dumps(receipt))
if __name__=='__main__':main()
