"use strict";
const CH="https://www.youtube.com/channel/UCp1bEH7DOpEjf_hjgCmZFlQ";
// ---- 安全のための点検（データは外から来るものとして扱い、決まった形のものだけを画面に出す）
const ID_RE=/^[\w-]{11}$/, TIME_RE=/^\d+:\d{2}(?::\d{2})?$/, TOWN="https://www.town.teshikaga.hokkaido.jp/";
const okImg=u=>typeof u==="string"&&(u.startsWith(TOWN)||u.startsWith("data:image/svg+xml,"));
const W=v=>"https://www.youtube.com/watch?v="+v.id;
const sec=t=>t.split(":").reduce((a,x)=>a*60+ +x,0);
const TRE=/(\d+:\d{2}(?::\d{2})?)(?!\d)/;
const itemText=(v,t,k)=>t?t.split(TRE).map((p,i)=>i%2?tl(v,p):hl(p,k)).join(""):"この場面から再生";
const memChip=n=>{const m=MEM[n];if(!m||typeof m!=="object"||typeof m.page!=="string"||!m.page.startsWith(TOWN))return"";const f=esc(m.full||n)+"議員";
 return '<a class="mem" href="'+esc(m.page)+'" target="_blank" rel="noopener" aria-label="'+f+'。弟子屈町公式サイトの議員名簿を新しいタブで開く">'
  +(okImg(m.photo)?'<img src="'+esc(m.photo)+'" alt="" width="56" height="72" loading="lazy">':'')
  +'<span>'+f+'<small>議員名簿（町公式サイト）</small></span></a>';};
const qBlock=(v,b,k)=>'<div class="qb"><p class="qh">'+(b.time?tl(v,b.time)+' ':'')+hl(b.label||"",k)+'</p>'
 +(b.q?'<p class="qq"><b>【質問事項】</b>'+hl(b.q,k)+'</p>':'')
 +(b.gist?'<details'+(k&&b.gist.toLowerCase().includes(k.toLowerCase())?' open':'')+'><summary>【質問要旨】</summary><p class="gist">'+hl(b.gist,k)+'</p></details>':'')+'</div>';
const tl=(v,t)=>{t=String(t);return v.id&&TIME_RE.test(t)?'<a class="t" href="'+W(v)+'&t='+sec(t)+'s" target="_blank" rel="noopener">'+t+'</a>':'<span class="t">'+esc(t)+'</span>'};
let V=[];
function prep(){
 const n0=V.length;
 V=V.filter(v=>v&&typeof v.title==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v.pub||"")).map(v=>{
  if(!ID_RE.test(v.id||""))v.id="";
  if(v.qs&&!Array.isArray(v.qs))delete v.qs;
  if(v.items&&!Array.isArray(v.items))delete v.items;
  if(v.qs)v.qs=v.qs.filter(b=>b&&typeof b==="object").map(b=>({time:String(b.time||""),label:String(b.label||""),q:String(b.q||""),gist:String(b.gist||"")}));
  if(v.items)v.items=v.items.filter(x=>Array.isArray(x)).map(x=>[String(x[0]||""),String(x[1]||"")]);
  return v;});
 if(V.length<n0)console.warn("形が正しくない動画データを"+(n0-V.length)+"件、表示から外しました");
// タイトルを読み取る（読めない部分は空のまま＝推測しない）
V.forEach((v,i)=>{
 const t=v.title;
 v._i=i;
 v.session=(t.match(/^(令和\d+年第\d+回(?:定例会|臨時会))/)||[])[1]||"未分類";
 const ry=+((t.match(/^令和(\d+)年/)||[])[1]||0);
 v.fy=ry;
 const kai=+((t.match(/第(\d+)回/)||[])[1]||0),dn=+((t.match(/(\d+)日目/)||[])[1]||0),cm=t.match(/[\u2460-\u2473]/);
 v.sk=ry*1e6+kai*1e4+dn*100+(cm?cm[0].charCodeAt(0)-0x245f:0);
 v.day=(t.match(/(\d+日目)/)||[])[1]||"";
 v.date=(t.match(/（(\d+\/\d+[^）]*)）/)||[])[1]||"";
 v.member=(t.match(/一般質問（(.+?)議員）/)||[])[1]||"";
 v.kind=kindOf(t);
 if(v.q&&!v.qs)v.qs=[{time:"",label:"",q:v.q,gist:v.gist||""}];   // 古い形のデータも読める
 v.text=[t,...(v.qs||[]).map(b=>b.label+" "+b.q+" "+b.gist),...(v.items||[]).map(x=>x[1])].join(" ");
});}
const list=document.getElementById("list"),count=document.getElementById("count"),q=document.getElementById("q");
const kindsEl=document.getElementById("kinds");
list.addEventListener("error",e=>{if(e.target&&e.target.tagName==="IMG")e.target.remove()},true);   // 写真が読めないときは、名前のリンクだけにする
let view="session",asc=false,kind="";
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function hl(s,k){   // 元の文字を先に分けてから、1つずつ安全な文字にする（「amp」などで表示が崩れない）
 s=String(s);if(!k)return esc(s);
 const re=new RegExp("("+k.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+")","gi");
 return s.split(re).map((p,i)=>i%2?"<mark>"+esc(p)+"</mark>":esc(p)).join("");
}
function card(v,k){
 let h='<article class="card"><h3>'+hl(v.title,k)+'</h3><p class="meta"><span class="tag">'+esc(v.kind)+'</span>'+'会議日 '+esc(v.date||"不明")+'　公開日 '+esc(v.pub.replace(/-/g,"/"))+'</p>';
 if(v.member&&view!=="member") h+=memChip(v.member);
 if(v.qs) h+=v.qs.map(b=>qBlock(v,b,k)).join("");
 if(v.items&&!v.qs) h+='<details'+(k?' open':'')+'><summary>この動画の内容（'+v.items.length+'件）</summary><ul class="items">'+v.items.map(x=>'<li>'+tl(v,x[0])+itemText(v,x[1],k)+'</li>').join("")+'</ul></details>';
 return h+'<p><a class="yt" href="'+(v.id?W(v):CH)+'" target="_blank" rel="noopener" aria-label="YouTubeに移動：'+esc(v.title)+'（新しいタブで開く）">YouTubeに移動</a></p></article>';
}
const fyName=v=>v.fy?"令和"+v.fy+"年":"年不明";
let YOMI={},MEM={};
// 動画の種類を決めるきまり。data/kinds.json があればそちらを使う（上から順に、タイトルに言葉が入っていた最初の種類になる）
let KR=[{name:"一般質問",title:["一般質問"]},{name:"予算特別委員会",title:["予算特別委員会"]},{name:"議案の審議",title:["議案"]}];
const kindOf=t=>{for(const r of KR)if((r.title||[]).some(w=>t.includes(w)))return r.name;return "その他"};
const cmpY=(a,b)=>(YOMI[a]||a).localeCompare(YOMI[b]||b,"ja");
const NUM=(a,b)=>b.localeCompare(a,"ja",{numeric:true});
function group(arr,keyf,order){
 const m={};arr.forEach(v=>{const g=keyf(v);(m[g]=m[g]||[]).push(v)});
 const ks=Object.keys(m);return order?ks.sort(order):ks;
}
function render(){
 const k=q.value.trim();
 const base=V.filter(v=>!k||v.text.toLowerCase().includes(k.toLowerCase()));
 const cnt={};base.forEach(v=>{cnt[v.kind]=(cnt[v.kind]||0)+1});
 const have=new Set(V.map(v=>v.kind)),names=[];                       // 種類のボタンは、データにある種類から自動で作る
 KR.forEach(r=>{if(have.has(r.name)&&!names.includes(r.name))names.push(r.name)});
 if(have.has("その他"))names.push("その他");
 kindsEl.innerHTML='<span class="meta" aria-hidden="true">種類：</span>'+[""].concat(names).map(n=>'<button type="button" class="kb" data-kind="'+esc(n)+'" aria-pressed="'+(kind===n)+'">'+esc(n||"全種類")+'（'+(n?(cnt[n]||0):base.length)+'）</button>').join("");
 let arr=kind?base.filter(v=>v.kind===kind):base;
 arr.sort((a,b)=>asc?a.sk-b.sk:b.sk-a.sk);
 let h="";
 if(view==="member"){
  arr=arr.filter(v=>v.member);
  group(arr,v=>v.member,(a,b)=>asc?cmpY(b,a):cmpY(a,b)).forEach(g=>{
   h+='<h2>'+esc(g)+'議員</h2>'+memChip(g)+arr.filter(v=>v.member===g).map(v=>card(v,k)).join("")});
  h+='<p class="meta">「議員別」には、タイトルに議員名がある動画（一般質問）だけが出ます。</p>';
 }else if(view==="year"){
  group(arr,fyName).forEach(g=>{
   const sub=arr.filter(v=>fyName(v)===g),n=sub[0].fy;
   h+='<h2>'+g+'</h2>'+(n?'<p class="meta">西暦'+(n+2018)+'年（1月～12月に開かれた会議）</p>':'');
   group(sub,v=>v.session).forEach(s=>{h+='<h3 class="sub">'+esc(s)+'</h3>'+sub.filter(v=>v.session===s).map(v=>card(v,k)).join("")})});
 }else if(view==="session"){
  group(arr,v=>v.session).forEach(g=>{
   h+='<h2>'+esc(g)+'</h2>'+arr.filter(v=>v.session===g).map(v=>card(v,k)).join("")});
 }else h=arr.map(v=>card(v,k)).join("");
 if(!arr.length||(view==="member"&&!arr.some(v=>v.member))) h='<p class="empty">条件に合う動画はありません。別の言葉で探してみてください。</p>'+(view==="member"?h:"");
 list.innerHTML=h;
 const ord=view==="member"?(asc?"あいうえお順（逆）":"あいうえお順"):(asc?"古い順":"新しい順");
 sortBtn.classList.toggle("flip",asc);
 sortBtn.setAttribute("aria-label","並べ替え。いまは"+ord+"。押すと逆になります");
 count.textContent=arr.length+"本の動画が見つかりました（"+ord+"）";
}
kindsEl.onclick=e=>{const b=e.target.closest("button[data-kind]");if(!b)return;const n=b.dataset.kind;kind=(n===kind)?"":n;render();
 const nb=[...kindsEl.querySelectorAll("button")].find(x=>x.dataset.kind===n);if(nb)nb.focus();};   // 押したあとも、同じボタンに操作が残るようにする
const sortBtn=document.getElementById("sort");
sortBtn.onclick=()=>{asc=!asc;render();};
document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>{
 view=b.dataset.view;
 document.querySelectorAll("[data-view]").forEach(x=>x.setAttribute("aria-pressed",x===b));
 render();
});
q.addEventListener("input",render);
const SZ=[14,16,18,21,24];let fi=2;   // 左から 小（2段階目）・小（1段階目）・標準（中）・大（1段階目）・大（2段階目）
const fss=document.getElementById("fss"),fsn=document.getElementById("fsn"),fsb=document.getElementById("fsb"),fsl=document.getElementById("fsl");
function setFs(){
 document.documentElement.style.setProperty("--fs",SZ[fi]+"px");
 fss.disabled=fi===0;fsb.disabled=fi===SZ.length-1;
 fss.setAttribute("aria-pressed",fi<2);fsn.setAttribute("aria-pressed",fi===2);fsb.setAttribute("aria-pressed",fi>2);
 fsl.textContent="文字サイズ："+(fi===2?"標準（中）":(fi<2?"小":"大")+"（"+Math.abs(fi-2)+"段階目）");
}
fss.onclick=()=>{if(fi>0){fi--;setFs();}};
fsb.onclick=()=>{if(fi<SZ.length-1){fi++;setFs();}};
fsn.onclick=()=>{fi=2;setFs();};
setFs();
document.getElementById("dark").onclick=e=>{
 const on=e.target.getAttribute("aria-pressed")!=="true";
 e.target.setAttribute("aria-pressed",on);
 document.documentElement.dataset.theme=on?"dark":"light";
};
fetch("data/members.json",{cache:"no-cache"}).then(r=>r.ok?r.json():{}).catch(()=>({})).then(m=>{MEM=m;YOMI={};for(const k in m)YOMI[k]=typeof m[k]==="string"?m[k]:(m[k].yomi||"");return fetch("data/kinds.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null).catch(()=>null).then(kj=>{if(kj&&Array.isArray(kj.rules))KR=kj.rules;return fetch("data/videos.json",{cache:"no-cache"})})}).then(r=>{if(!r.ok)throw 0;return r.json()}).then(d=>{
 V=d.videos;prep();document.getElementById("upd").textContent="最終更新："+d.updated;render();
}).catch(()=>{list.innerHTML='<p class="empty">動画の情報を読み込めませんでした。時間をおいて、もう一度開いてください。</p>'});
