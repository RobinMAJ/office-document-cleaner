const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');const assert=require('node:assert/strict');const {test}=require('node:test');
const root=path.resolve(__dirname,'..');const JSZip=require(path.join(root,'site/assets/vendor/jszip.min.js'));
const source=fs.readFileSync(path.join(root,'site/assets/app.js'),'utf8').split('/*LOGIC-END*/')[0];
const ctx={Date,Uint8Array,ArrayBuffer,Buffer,setTimeout,clearTimeout};vm.createContext(ctx);vm.runInContext(source+'\nthis.api={loadDoc,buildDoc};',ctx);const {loadDoc,buildDoc}=ctx.api;
const opts={stats:true,rsid:true,authors:true,paths:true,custom:true,thumb:true};
for(const kind of ['docx','xlsx','pptx']){
 test(`${kind}: metadata removal preserves content and produces a readable package`,async()=>{
  const input=fs.readFileSync(path.join(__dirname,'fixtures','sample.'+kind));const d=await loadDoc(JSZip,input);assert.equal(d.kind,kind);assert.equal(d.meta.creator,'Fixture Author');assert.equal(d.found.custom,1);
  const output=await buildDoc(JSZip,d,{},opts,'uint8array');const z=await JSZip.loadAsync(output);const checked=await loadDoc(JSZip,output);assert.equal(checked.meta.creator,'');assert.equal(checked.meta.lastModifiedBy,'');assert.equal(checked.meta.created,'');assert.equal(checked.meta.modified,'');assert.equal(checked.found.custom,0);assert.equal(z.file('docProps/custom.xml'),null);
  const inputZip=await JSZip.loadAsync(input);const contentPaths=kind==='docx'?['word/document.xml']:kind==='xlsx'?['xl/worksheets/sheet1.xml']:['ppt/slides/slide1.xml'];
  for(const p of contentPaths){const clean=s=>s.replace(/ w:rsid[A-Za-z]*="[^"]*"/g,'');assert.equal(clean(await z.file(p).async('string')),clean(await inputZip.file(p).async('string')));}
  if(kind==='xlsx'){const comments=await z.file('xl/comments/comment1.xml').async('string');assert.ok(comments.includes('Keep this comment text.'));assert.ok(comments.includes('<author>Author</author>'));}
  fs.mkdirSync(path.join(__dirname,'outputs'),{recursive:true});fs.writeFileSync(path.join(__dirname,'outputs','clean.'+kind),Buffer.from(output));
 });
 test(`${kind}: replacing authors and timestamps retains requested values`,async()=>{
  const d=await loadDoc(JSZip,fs.readFileSync(path.join(__dirname,'fixtures','sample.'+kind)));const output=await buildDoc(JSZip,d,{creator:'Updated Author',created:'2000-01-01T00:00:00Z',modified:'2000-01-01T00:00:00Z',revision:'1'},opts,'uint8array');const check=await loadDoc(JSZip,output);assert.equal(check.meta.creator,'Updated Author');assert.equal(check.meta.created,'2000-01-01T00:00:00Z');assert.equal(check.meta.revision,'1');
 });
}
test('Unsupported and corrupt files give controlled errors',async()=>{await assert.rejects(loadDoc(JSZip,Buffer.from('not a zip')),/NOT_ZIP/);const z=new JSZip();z.file('not-office.txt','test');await assert.rejects(loadDoc(JSZip,await z.generateAsync({type:'uint8array'})),/NOT_OOXML/);});
