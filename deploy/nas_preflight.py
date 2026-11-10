from pathlib import Path
import json,os,socket,subprocess,sys,importlib.util
root=Path('/config/workspace')
runtime=root/'ChiLi-NanoSym/envs/chili-light/bin/python'
binroot=root/'project_AI4oribital_A1/deployment/llm-20260920-v1/network-bin'
ports={}
for port in (18815,28734):
 with socket.socket() as s:
  try:s.bind(('127.0.0.1',port));ports[str(port)]='available'
  except OSError:ports[str(port)]='occupied'
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
 try:s.bind(('0.0.0.0',41660));ports['udp41660']='available'
 except OSError:ports['udp41660']='occupied'
versions=subprocess.run([str(runtime),'-c','import django,gunicorn,json;print(json.dumps({"django":django.get_version(),"gunicorn":gunicorn.__version__}))'],capture_output=True,text=True,timeout=12)
records={}
for name,sock in {'a1':'/tmp/a1-llm-tailscale.sock','orbital':'/tmp/jiabino11-orbital.sock','chili':'/tmp/jiabin-chili.sock','palette':'/tmp/scientific-palette-tailscale.sock'}.items():
 p=subprocess.run([str(binroot/'tailscale'),'--socket='+sock,'status','--json'],capture_output=True,text=True,timeout=8)
 try:
  d=json.loads(p.stdout);records[name]={'state':d.get('BackendState'),'dns':d.get('Self',{}).get('DNSName'),'node_id':d.get('Self',{}).get('ID')}
 except Exception:records[name]={'state':'unavailable'}
print(json.dumps({'uid':os.getuid(),'root_exists':(root/'office-document-cleaner').exists(),'runtime':str(runtime),'versions':json.loads(versions.stdout) if versions.returncode==0 else {'error':'runtime_import_failed'},'ports':ports,'nodes':records,'new_socket_exists':Path('/tmp/office-document-cleaner.sock').exists(),'public_routes_modified':False}))
