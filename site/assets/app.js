
/*LOGIC-START*/
const NS={cp:"http://schemas.openxmlformats.org/package/2006/metadata/core-properties",dc:"http://purl.org/dc/elements/1.1/",dcterms:"http://purl.org/dc/terms/",dcmitype:"http://purl.org/dc/dcmitype/",xsi:"http://www.w3.org/2001/XMLSchema-instance"};
const REL_CORE="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties";
const REL_APP="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties";
const REL_CUSTOM="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties";
const REL_THUMB="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail";
const CT_CORE="application/vnd.openxmlformats-package.core-properties+xml";
const CT_APP="application/vnd.openxmlformats-officedocument.extended-properties+xml";
const NS_APP="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties";
const NS_VT="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes";
const CORE_FIELDS=[["creator","dc"],["lastModifiedBy","cp"],["title","dc"],["subject","dc"],["keywords","cp"],["description","dc"],["category","cp"],["created","dcterms"],["modified","dcterms"],["lastPrinted","cp"],["revision","cp"]];
const APP_FIELDS=["TotalTime","Company","Manager","Application","AppVersion","Template"];
const XML_HEAD='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';

function xesc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function xunesc(s){return s.replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&apos;/g,"'").replace(/&#(\d+);/g,(m,d)=>String.fromCodePoint(+d)).replace(/&#x([0-9a-fA-F]+);/g,(m,h)=>String.fromCodePoint(parseInt(h,16))).replace(/&amp;/g,"&")}
function readTag(xml,name){const m=new RegExp("<(?:[\\w]+:)?"+name+"(?:\\s[^>]*)?>([\\s\\S]*?)</(?:[\\w]+:)?"+name+">").exec(xml||"");return m?xunesc(m[1]).trim():""}
function relTarget(rels,type){const re=/<Relationship\b[^>]*>/g;let m;while((m=re.exec(rels||""))){if(m[0].includes('Type="'+type+'"')){const t=/Target="([^"]*)"/.exec(m[0]);if(t)return t[1].replace(/^\//,"")}}return null}
function dropRel(rels,type){return rels.replace(/<Relationship\b[^>]*\/>/g,t=>t.includes('Type="'+type+'"')?"":t)}
function dropOverride(ct,path){return ct.replace(/<Override\b[^>]*\/>/g,t=>t.includes('PartName="/'+path+'"')?"":t)}
function genCore(v){
  let s=XML_HEAD+'<cp:coreProperties xmlns:cp="'+NS.cp+'" xmlns:dc="'+NS.dc+'" xmlns:dcterms="'+NS.dcterms+'" xmlns:dcmitype="'+NS.dcmitype+'" xmlns:xsi="'+NS.xsi+'">';
  for(const [k,p] of CORE_FIELDS){const val=(v[k]||"").trim();if(!val)continue;
    const attr=p==="dcterms"?' xsi:type="dcterms:W3CDTF"':"";s+="<"+p+":"+k+attr+">"+xesc(val)+"</"+p+":"+k+">"}
  return s+"</cp:coreProperties>";
}
function genApp(v){let s=XML_HEAD+'<Properties xmlns="'+NS_APP+'" xmlns:vt="'+NS_VT+'">';
  for(const k of APP_FIELDS){const val=(v[k]||"").trim();if(val)s+="<"+k+">"+xesc(val)+"</"+k+">"}
  return s+"</Properties>"}
function setAppTag(xml,k,val){
  xml=xml.replace(new RegExp("<"+k+"(?:\\s[^>]*)?>[\\s\\S]*?</"+k+">|<"+k+"(?:\\s[^>]*)?/>","g"),"");
  val=(val||"").trim();if(!val)return xml;
  xml=xml.replace(/<Properties\b([^>]*)\/>\s*$/,"<Properties$1></Properties>");
  return xml.replace(/<\/Properties>\s*$/,"<"+k+">"+xesc(val)+"</"+k+"></Properties>");
}
function scanParts(kind,names){
  if(kind==="docx")return names.filter(n=>/^word\/[^\/]+\.xml$/.test(n));
  if(kind==="xlsx")return names.filter(n=>/^xl\/(workbook\.xml|(.*\/)?[^\/]*comment[^\/]*\.xml|persons\/[^\/]+\.xml)$/i.test(n));
  return names.filter(n=>/^ppt\/(commentAuthors\.xml|authors\.xml)$/.test(n));
}
async function loadDoc(JSZip,buf){
  let zip;try{zip=await JSZip.loadAsync(buf)}catch(e){throw new Error("NOT_ZIP")}
  const kind=zip.file("word/document.xml")?"docx":zip.file("xl/workbook.xml")?"xlsx":zip.file("ppt/presentation.xml")?"pptx":null;
  if(!kind)throw new Error("NOT_OOXML");
  const str=async p=>zip.file(p)?await zip.file(p).async("string"):"";
  const rels=await str("_rels/.rels");
  const corePath=relTarget(rels,REL_CORE)||"docProps/core.xml", appPath=relTarget(rels,REL_APP)||"docProps/app.xml";
  const core=await str(corePath), app=await str(appPath);
  const meta={};for(const [k] of CORE_FIELDS)meta[k]=readTag(core,k);for(const k of APP_FIELDS)meta[k]=readTag(app,k);
  const names=Object.keys(zip.files).filter(n=>!zip.files[n].dir);
  const found={rsid:0,authors:[],paths:[],custom:0,thumb:false,stats:0};
  const authors=new Set();
  for(const n of scanParts(kind,names)){
    const x=await str(n);let m;
    if(kind==="docx"){
      found.rsid+=(x.match(/ w:rsid[A-Za-z]*="/g)||[]).length+(x.match(/<w:rsid(?:Root)? /g)||[]).length;
      const re=/\bw(?:15)?:author="([^"]*)"/g;while((m=re.exec(x)))if(m[1])authors.add(xunesc(m[1]));
    }else if(kind==="xlsx"){
      let re=/<author>([^<]*)<\/author>/g;while((m=re.exec(x)))if(m[1])authors.add(xunesc(m[1]));
      re=/displayName="([^"]*)"/g;while((m=re.exec(x)))if(m[1])authors.add(xunesc(m[1]));
      re=/<x15ac:absPath\b[^>]*url="([^"]*)"/g;while((m=re.exec(x)))found.paths.push(xunesc(m[1]));
    }else{
      const re=/<(?:p:cmAuthor|p188:author)\b[^>]*\bname="([^"]*)"/g;while((m=re.exec(x)))if(m[1])authors.add(xunesc(m[1]));
    }
  }
  if(kind==="docx"){const sr=await str("word/_rels/settings.xml.rels");const re=/<Relationship\b[^>]*attachedTemplate[^>]*>/g;let m;while((m=re.exec(sr))){const t=/Target="([^"]*)"/.exec(m[0]);if(t)found.paths.push(xunesc(t[1]))}}
  found.authors=[...authors];
  const cp=relTarget(rels,REL_CUSTOM);if(cp&&zip.file(cp))found.custom=((await str(cp)).match(/<property\b/g)||[]).length||1;
  const tp=relTarget(rels,REL_THUMB);found.thumb=!!(tp&&zip.file(tp));
  found.stats=(app.match(/<(Pages|Words|Characters|Lines|Paragraphs|CharactersWithSpaces|Slides|Notes|HiddenSlides|TitlesOfParts|HeadingPairs)\b/g)||[]).length;
  return {zip,kind,corePath,appPath,meta,found};
}
async function buildDoc(JSZip,doc,values,opts,outType){
  const {zip,kind,corePath,appPath}=doc;const text={},removed=new Set();
  const get=async p=>p in text?text[p]:(zip.file(p)?(text[p]=await zip.file(p).async("string")):null);
  const names=Object.keys(zip.files).filter(n=>!zip.files[n].dir);
  let rels=(await get("_rels/.rels"))||XML_HEAD+'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>';
  let ct=await get("[Content_Types].xml");
  const register=(path,type,ctype,id)=>{
    if(!rels.includes('Type="'+type+'"'))rels=rels.replace(/<\/Relationships>\s*$/,'<Relationship Id="'+id+'" Type="'+type+'" Target="'+path+'"/></Relationships>');
    if(!ct.includes('PartName="/'+path+'"'))ct=ct.replace(/<\/Types>\s*$/,'<Override PartName="/'+path+'" ContentType="'+ctype+'"/></Types>');
  };
  // core properties: always regenerated from the form
  text[corePath]=genCore(values);
  if(!zip.file(corePath))register(corePath,REL_CORE,CT_CORE,"rIdCoreProps");
  // extended properties
  const hasApp=!!zip.file(appPath), anyApp=APP_FIELDS.some(k=>(values[k]||"").trim());
  if(hasApp){
    if(opts.stats)text[appPath]=genApp(values);
    else{let a=await get(appPath);for(const k of APP_FIELDS)a=setAppTag(a,k,values[k]);text[appPath]=a}
  }else if(anyApp){text[appPath]=genApp(values);register(appPath,REL_APP,CT_APP,"rIdAppProps")}
  // hidden traces
  for(const n of scanParts(kind,names)){
    let x=await get(n);const before=x;
    if(kind==="docx"){
      if(opts.rsid)x=x.replace(/ w:rsid[A-Za-z]*="[^"]*"/g,"").replace(/<w:rsids>[\s\S]*?<\/w:rsids>/g,"").replace(/<w:rsid w:val="[^"]*"\/>/g,"");
      if(opts.authors)x=x.replace(/\b(w(?:15)?:author)="[^"]*"/g,'$1="Author"').replace(/ w:initials="[^"]*"/g,' w:initials="A"').replace(/ w:date="[^"]*"/g,"").replace(/ w16du:dateUtc="[^"]*"/g,"").replace(/ w16cex:dateUtc="[^"]*"/g,"").replace(/<w15:presenceInfo\b[^>]*\/>/g,"");
      if(opts.paths&&n==="word/settings.xml")x=x.replace(/<w:attachedTemplate\b[^>]*\/>/g,"");
    }else if(kind==="xlsx"){
      if(opts.authors)x=x.replace(/<author>[^<]*<\/author>/g,"<author>Author</author>").replace(/displayName="[^"]*"/g,'displayName="Author"').replace(/userId="[^"]*"/g,'userId=""');
      if(opts.paths)x=x.replace(/<mc:AlternateContent\b[^>]*>\s*<mc:Choice\b[^>]*>\s*<x15ac:absPath\b[^>]*\/>\s*<\/mc:Choice>\s*<\/mc:AlternateContent>/g,"");
    }else if(opts.authors){
      x=x.replace(/<(p:cmAuthor|p188:author)\b[^>]*>/g,t=>t.replace(/\bname="[^"]*"/,'name="Author"').replace(/\binitials="[^"]*"/,'initials="A"').replace(/\buserId="[^"]*"/,'userId=""'));
    }
    if(x===before)delete text[n];else text[n]=x;
  }
  if(kind==="docx"&&opts.paths){const p="word/_rels/settings.xml.rels";const sr=await get(p);if(sr){const nx=sr.replace(/<Relationship\b[^>]*attachedTemplate[^>]*\/>/g,"");if(nx===sr)delete text[p];else text[p]=nx}}
  if(opts.custom){const p=relTarget(rels,REL_CUSTOM);if(p){removed.add(p);rels=dropRel(rels,REL_CUSTOM);ct=dropOverride(ct,p)}}
  if(opts.thumb){const p=relTarget(rels,REL_THUMB);if(p){removed.add(p);rels=dropRel(rels,REL_THUMB)}}
  text["_rels/.rels"]=rels;text["[Content_Types].xml"]=ct;
  // rebuild the package with neutral timestamps on every entry
  const out=new JSZip(),stamp=new Date(Date.UTC(1980,0,2));
  const all=names.concat(Object.keys(text).filter(n=>!names.includes(n)));
  for(const n of all){if(removed.has(n))continue;
    out.file(n,n in text?text[n]:await zip.file(n).async("uint8array"),{date:stamp,createFolders:false})}
  return out.generateAsync({type:outType||"blob",compression:"DEFLATE",compressionOptions:{level:6}});
}
/*LOGIC-END*/

/* ---------- interface ---------- */
const $=id=>document.getElementById(id);
const GROUPS=[
  ["人员",[["creator","作者","text"],["lastModifiedBy","上次保存者","text"],["Company","单位","text"],["Manager","经理","text"]]],
  ["时间与修订",[["created","创建时间","date"],["modified","修改时间","date"],["lastPrinted","打印时间","date"],["revision","修订号","int"],["TotalTime","编辑时间总计（分钟）","int"]]],
  ["描述",[["title","标题","text"],["subject","主题","text"],["keywords","关键词","text"],["description","备注","text"],["category","类别","text"]]],
  ["软件",[["Application","程序名称","text"],["AppVersion","程序版本","ver"],["Template","模板","text"]]]
];
const OPTS=[
  ["stats","删除统计信息","页数、字数、段落数等，以及表格名、幻灯片标题列表"],
  ["rsid","删除编辑痕迹标识","Word 给每次编辑打的内部编号（仅 Word）"],
  ["authors","批注和修订改为匿名","把支持的批注、修订姓名改成 Author；部分格式可去掉时间"],
  ["paths","删除本机路径","Excel 记录的保存路径、Word 记录的模板路径，里面常带电脑用户名"],
  ["custom","删除自定义属性","公司模板或插件写入的额外属性"],
  ["thumb","删除缩略图","文件里内嵌的首页预览图"]
];
const SAMPLE={kind:"docx",meta:{creator:"Zhang San",lastModifiedBy:"Zhang San",Company:"Example University",Manager:"",created:"2026-11-10T11:50:00Z",modified:"2026-11-10T12:35:00Z",lastPrinted:"",revision:"75",TotalTime:"12",title:"",subject:"",keywords:"",description:"",category:"",Application:"Microsoft Office Word",AppVersion:"16.0000",Template:"Normal.dotm"},
  found:{rsid:214,authors:["Zhang San"],paths:[],custom:0,thumb:false,stats:6}};
let doc=null,srcName="",pendingDownloadUrl=null;

const pad=n=>String(n).padStart(2,"0");
function isoToLocal(iso){if(!iso)return"";const d=new Date(iso);if(isNaN(d))return"";return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+"T"+pad(d.getHours())+":"+pad(d.getMinutes())+":"+pad(d.getSeconds())}
function localToIso(v){if(!v)return"";const d=new Date(v);if(isNaN(d))return"";return d.toISOString().replace(/\.\d+Z$/,"Z")}
const shown=(type,raw)=>type==="date"?isoToLocal(raw):raw;

function buildForm(){
  const host=$("fields");
  for(const [title,rows] of GROUPS){
    const g=document.createElement("div");g.className="group";
    const h=document.createElement("h3");h.textContent=title;g.appendChild(h);
    for(const [k,label,type] of rows){
      const r=document.createElement("div");r.className="row";r.dataset.k=k;r.dataset.type=type;
      const l=document.createElement("label");l.htmlFor="f-"+k;l.textContent=label;
      const c=document.createElement("div");c.className="cell";
      const i=document.createElement("input");i.id="f-"+k;i.disabled=true;i.autocomplete="off";
      if(type==="date"){i.type="datetime-local";i.step="1"}else{i.type="text";if(type==="int")i.inputMode="numeric";if(type==="ver")i.placeholder="例如 16.0000"}
      const o=document.createElement("div");o.className="orig";
      c.append(i,o);
      const x=document.createElement("button");x.type="button";x.className="x";x.textContent="清空";x.disabled=true;x.setAttribute("aria-label","清空"+label);
      x.addEventListener("click",()=>{i.value="";mark(r)});
      i.addEventListener("input",()=>mark(r));
      r.append(l,c,x);g.appendChild(r);
    }
    host.appendChild(g);
  }
  const ol=$("opts");
  for(const [k,label,hint] of OPTS){
    const li=document.createElement("li");li.dataset.k=k;
    li.innerHTML='<label><input type="checkbox" id="o-'+k+'" disabled><span><span>'+label+'</span><span class="found" id="of-'+k+'"></span></span></label>';
    li.title=hint;ol.appendChild(li);
  }
}
function mark(r){
  const i=r.querySelector("input"),orig=r.dataset.orig||"";
  r.classList.toggle("changed",i.value!==orig);r.classList.remove("bad");
  r.querySelector(".orig").textContent="原值："+(orig?orig.replace("T"," "):"（空）");
}
function fill(d,live){
  for(const r of document.querySelectorAll(".row")){
    const i=r.querySelector("input"),v=shown(r.dataset.type,d.meta[r.dataset.k]||"");
    i.value=v;r.dataset.orig=i.value;i.disabled=!live;r.querySelector(".x").disabled=!live;mark(r);
  }
  const f=d.found,k=d.kind;
  const say={stats:f.stats?"发现 "+f.stats+" 项":"未发现",
    rsid:k!=="docx"?"此类型没有":f.rsid?"发现 "+f.rsid+" 处":"未发现",
    authors:f.authors.length?"发现："+f.authors.join("、"):"未发现",
    paths:k==="pptx"?"此类型没有":f.paths.length?"发现："+f.paths.join("；"):"未发现",
    custom:f.custom?"发现 "+f.custom+" 项":"未发现",thumb:f.thumb?"发现":"未发现"};
  const hit={stats:f.stats,rsid:f.rsid,authors:f.authors.length,paths:f.paths.length,custom:f.custom,thumb:f.thumb};
  for(const [o] of OPTS){const el=$("of-"+o),cb=$("o-"+o);el.textContent=say[o];el.classList.toggle("hit",!!hit[o]);
    cb.disabled=!live;cb.checked=live&&!!hit[o]&&o!=="stats";cb.closest("li").classList.toggle("na",!hit[o])}
}
function status(msg,cls){const s=$("status");s.textContent=msg;s.className=cls||""}

async function openFile(file){
  if(!file)return;
  const ext=(file.name.split(".").pop()||"").toLowerCase();
  if(!["docx","xlsx","pptx"].includes(ext)){status("不支持这个文件：只能处理 .docx、.xlsx、.pptx。旧格式 .doc、.xls、.ppt 请先在 Office 里另存为新格式。","err");return}
  try{
    doc=await loadDoc(JSZip,await file.arrayBuffer());srcName=file.name;
    if(pendingDownloadUrl){URL.revokeObjectURL(pendingDownloadUrl);pendingDownloadUrl=null;}
    $("download-ready").hidden=true;$("download-ready").removeAttribute("href");
    $("kind").textContent=doc.kind;$("kind").className="badge";$("fname").textContent=file.name;
    fill(doc,true);
    $("property-mode").textContent="正在编辑";
    $("outname").value=file.name.replace(/\.[^.]+$/,"")+"_clean."+doc.kind;
    for(const id of ["wipe","stamp","reset","save","outname"])$(id).disabled=false;
    status("已读取。直接改右边的值，或点一键抹除全部，然后生成并保存。");
  }catch(e){
    status(e.message==="NOT_ZIP"?"读不了这个文件：它可能已损坏，或设置了打开密码。加密的文件请先在 Office 里去掉密码。":e.message==="NOT_OOXML"?"这不是有效的 Word、Excel 或 PowerPoint 文件。":"读取失败："+e.message,"err");
  }
}
function collect(){
  const v={};let bad=null;
  for(const r of document.querySelectorAll(".row")){
    const k=r.dataset.k,t=r.dataset.type,raw=r.querySelector("input").value.trim();let ok=true;
    if(t==="date")v[k]=localToIso(raw);
    else{v[k]=raw;if(raw&&t==="int")ok=/^\d{1,9}$/.test(raw)&&(k!=="revision"||+raw>0);if(raw&&t==="ver")ok=/^\d{1,2}\.\d{4}$/.test(raw)}
    r.classList.toggle("bad",!ok);if(!ok&&!bad)bad=r;
  }
  if(bad){const panel=bad.closest('[role="tabpanel"]');if(panel&&panel.hidden)document.getElementById(panel.getAttribute("aria-labelledby"))?.click();bad.querySelector("input").focus();const name=bad.querySelector("label").textContent;
    throw new Error(bad.dataset.type==="ver"?name+"的格式应为两位数字加四位小数，例如 16.0000。":name+"只能填"+(bad.dataset.k==="revision"?"大于 0 的":"")+"整数。")}
  const o={};for(const [k] of OPTS)o[k]=$("o-"+k).checked;
  return {v,o};
}
async function save(){
  if(!doc)return;let c;
  try{c=collect()}catch(e){status(e.message,"err");return}
  let name=$("outname").value.trim()||("clean."+doc.kind);
  if(!name.toLowerCase().endsWith("."+doc.kind))name+="."+doc.kind;
  $("save").disabled=true;status("正在生成…");
  try{
    const blob=await buildDoc(JSZip,doc,c.v,c.o,"blob");
    if(pendingDownloadUrl)URL.revokeObjectURL(pendingDownloadUrl);
    pendingDownloadUrl=URL.createObjectURL(blob);
    const a=$("download-ready");a.href=pendingDownloadUrl;a.download=name;a.hidden=false;
    a.click();
    status("已生成 "+name+"，请查看浏览器下载列表。文件始终在你的设备上处理。","ok");
  }catch(e){
    status("生成或下载失败："+(e&&e.message||e)+"。请检查浏览器是否允许下载后重试。","err");
  }finally{$("save").disabled=false}
}

buildForm();fill(SAMPLE,false);
$("file").addEventListener("change",e=>{openFile(e.target.files[0]);e.target.value=""});
const dz=$("drop");
["dragenter","dragover"].forEach(t=>dz.addEventListener(t,e=>{e.preventDefault();dz.classList.add("over")}));
["dragleave","drop"].forEach(t=>dz.addEventListener(t,e=>{e.preventDefault();dz.classList.remove("over")}));
dz.addEventListener("drop",e=>openFile(e.dataTransfer.files[0]));
$("wipe").addEventListener("click",()=>{
  for(const r of document.querySelectorAll(".row")){r.querySelector("input").value="";mark(r)}
  for(const [k] of OPTS)$("o-"+k).checked=true;
  status("所有属性已清空，隐藏痕迹已全部勾选。点生成并保存写出文件。");
});
$("stamp").addEventListener("click",()=>{
  for(const k of ["created","modified"]){const i=$("f-"+k);i.value="2000-01-01T00:00:00";mark(i.closest(".row"))}
  status("创建时间和修改时间已填为 2000-01-01 00:00:00，Word 会显示这个固定值。想用别的时间可以直接在格子里改。");
});
$("reset").addEventListener("click",()=>{if(doc){fill(doc,true);status("已恢复为文件里的原值。")}});
$("save").addEventListener("click",save);

// System-like appearance control. Only the appearance preference is stored.
$("theme-toggle").addEventListener("click",()=>{
  const dark=document.documentElement.dataset.theme!=="dark";
  document.documentElement.dataset.theme=dark?"dark":"light";
  $("theme-toggle").setAttribute("aria-pressed",String(dark));
  $("theme-toggle").setAttribute("aria-label",dark?"切换为浅色外观":"切换为深色外观");
});

// Keep all real property fields in the document; tabs only change visibility.
// Existing collect/reset/clear handlers continue to operate on every field.
(()=>{
  const host=$("fields"),groups=[...host.querySelectorAll(":scope > .group")];
  const tabs=document.createElement("div");tabs.className="property-tabs";
  tabs.setAttribute("role","tablist");tabs.setAttribute("aria-label","文档属性分类");
  const buttons=groups.map((group,index)=>{
    const button=document.createElement("button");button.type="button";
    button.textContent=group.querySelector("h3").textContent;
    button.id="property-tab-"+index;button.setAttribute("role","tab");
    group.id="property-panel-"+index;group.setAttribute("role","tabpanel");
    group.setAttribute("aria-labelledby",button.id);
    button.setAttribute("aria-controls",group.id);
    button.addEventListener("click",()=>select(index));tabs.append(button);return button;
  });
  function select(index){groups.forEach((group,i)=>{
    group.hidden=i!==index;buttons[i].setAttribute("aria-selected",String(i===index));
    buttons[i].tabIndex=i===index?0:-1;
  });}
  tabs.addEventListener("keydown",event=>{
    const index=buttons.indexOf(event.target);
    if(index<0||!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;
    event.preventDefault();const next=event.key==="Home"?0:event.key==="End"?buttons.length-1:(index+(event.key==="ArrowRight"?1:-1)+buttons.length)%buttons.length;
    select(next);buttons[next].focus();
  });
  host.prepend(tabs);select(0);
})();

window.addEventListener("pagehide",()=>{if(pendingDownloadUrl)URL.revokeObjectURL(pendingDownloadUrl);});
