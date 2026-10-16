var ASSETS=["GC","NQ","ES"];
var ITEMS=[
{id:"mkt",g:"htf",t:"MARKET: GOLD / NQ / ES",w:2,auto:true},
{id:"struct",g:"htf",t:"MARKET STRUCTURE HTF (UP / DOWN) موافق للاتجاه",w:8},
{id:"idm",g:"htf",t:"IDM / LQ MAPS HTF",w:8},
{id:"poi",g:"htf",t:"POI HTF",w:14},
{id:"smt",g:"htf",t:"SMT HTF",w:8},
{id:"nonews",g:"htf",t:"NO NEWS (60 دقيقة)",w:6,auto:true},
{id:"ses",g:"htf",t:"SESSION: NEW YORK",w:4,auto:true},
{id:"bias",g:"htf",t:"DAILY BIAS 1D / 1W / 1M موافق للاتجاه",w:8},
{id:"fibo",g:"htf",t:"FIBO ZONE (Long: DISCOUNT / Short: PREMIUM) + VOLUME PROFILE HTF",w:6},
{id:"sweep",g:"ltf",t:"SWEEP / LQ",w:10},
{id:"smt2",g:"ltf",t:"SMT",w:8},
{id:"poi2",g:"ltf",t:"POI",w:10},
{id:"choch",g:"ltf",t:"CHoCH / MSS على 1M / 5M",w:8,x:true},
{id:"sl",g:"risk",t:"SL محدد منطقي (ورا الـ POI)",w:4,x:true},
{id:"rr",g:"risk",t:"RR ≥ 1:2",w:6,auto:true,x:true},
{id:"riskpct",g:"risk",t:"المخاطرة ≤ 1% وما وصلتش حد الخسارة اليومي",w:4,x:true},
{id:"newsbias",g:"ctx",t:"الأخبار كتدعم الاتجاه (من الدشبورد)",w:4,auto:true,x:true}
];
var AUTO=["mkt","ses","nonews","rr","newsbias"];
var GROUPS=["htf","ltf","risk","ctx"];
var BANDS=["ضعيفة","متوسطة","جيدة","قوية"];
var KEY="plan_journal_v1";
var S={dir:"long",ck:{},manual:{},news:[],evts:[],rrInvalid:false,evtMsg:"",last:null};

function $(id){return document.getElementById(id)}
function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
function num(id){var v=parseFloat($(id).value);return isNaN(v)?null:v}
function band(p){return p<50?0:p<70?1:p<85?2:3}
function jload(){try{var a=JSON.parse(localStorage.getItem(KEY)||"[]");return Array.isArray(a)?a:[]}catch(e){return[]}}
function jsave(a){try{localStorage.setItem(KEY,JSON.stringify(a))}catch(e){}}
function fmt(ts){return new Date(ts).toLocaleString("en-GB",{timeZone:"Africa/Casablanca",day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"})}
function resetAuto(){AUTO.forEach(function(k){S.manual[k]=false})}

function inNY(){
  var p=new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",weekday:"short",hour:"2-digit",hour12:false}).formatToParts(new Date());
  var wd="",h=0;
  p.forEach(function(x){if(x.type==="weekday")wd=x.value;if(x.type==="hour")h=parseInt(x.value,10)%24});
  return ["Mon","Tue","Wed","Thu","Fri"].indexOf(wd)>-1&&h>=7&&h<12;
}

function syncDir(){
  Array.prototype.forEach.call(document.querySelectorAll("[data-dir]"),function(b){
    b.className="seg-btn"+(b.getAttribute("data-dir")===S.dir?" on":"");
  });
}

function build(){
  var sel=$("asset");
  ASSETS.forEach(function(a){var o=document.createElement("option");o.value=a;o.textContent=a;sel.appendChild(o)});
  sel.addEventListener("change",function(){resetAuto();refresh()});
  ["entry","sl","tp"].forEach(function(id){$(id).addEventListener("input",function(){resetAuto();refresh()})});
  Array.prototype.forEach.call(document.querySelectorAll("[data-dir]"),function(b){
    b.addEventListener("click",function(){S.dir=b.getAttribute("data-dir");syncDir();resetAuto();refresh()});
  });
  GROUPS.forEach(function(g){
    var box=$("g_"+g);
    ITEMS.filter(function(i){return i.g===g}).forEach(function(i){
      var row=el("label","item"),cb=document.createElement("input");
      cb.type="checkbox";cb.id="ck_"+i.id;
      cb.addEventListener("change",function(){S.ck[i.id]=cb.checked;S.manual[i.id]=true;calc()});
      row.appendChild(cb);
      row.appendChild(el("span","txt",i.t));
      if(i.auto)row.appendChild(el("span","badge","تلقائي"));
      if(i.x)row.appendChild(el("span","badge","إضافة"));
      row.appendChild(el("span","w ltr","+"+i.w));
      box.appendChild(row);
    });
  });
  $("btnSave").addEventListener("click",saveTrade);
  $("btnReset").addEventListener("click",resetAll);
  $("btnCopy").addEventListener("click",copyData);
  syncDir();
}

function newsScore(asset){
  var sc=0;
  S.news.forEach(function(n){
    if(!n.ts)return;
    var h=(Date.now()-n.ts)/3600000;
    if(h>48)return;
    var w=Math.pow(0.5,h/6);
    (n.impacts||[]).forEach(function(i){
      if(i.asset===asset)sc+=(i.direction==="up"?1:i.direction==="down"?-1:0)*(i.strength||0)*w;
    });
  });
  return Math.round(sc*10)/10;
}

function evtRisk(){
  var now=Date.now(),hit=null;
  S.evts.forEach(function(e){
    var d=(e.ts-now)/60000;
    if(d<=60&&d>=-15&&(!hit||e.ts<hit.ts))hit=e;
  });
  if(!hit)return "";
  var m=Math.round((hit.ts-now)/60000);
  return "حدث قريب: "+hit.title+(m>=0?" بعد "+m+" دقيقة":" وقع دابا");
}

function refresh(){
  var asset=$("asset").value,en=num("entry"),sl=num("sl"),tp=num("tp"),rr=null;
  S.rrInvalid=false;
  if(en!==null&&sl!==null&&tp!==null){
    var ok=S.dir==="long"?(sl<en&&en<tp):(tp<en&&en<sl);
    if(ok){rr=Math.abs(tp-en)/Math.abs(en-sl)}else{S.rrInvalid=true}
  }
  $("rrout").textContent=rr===null?"--":"1 : "+(Math.round(rr*100)/100);
  var ns=newsScore(asset);
  var aligned=S.dir==="long"?ns>=0.5:ns<=-0.5;
  S.evtMsg=evtRisk();
  var ny=inNY();
  var auto={mkt:ASSETS.indexOf(asset)>-1,ses:ny,nonews:!S.evtMsg,rr:rr!==null&&rr>=2,newsbias:aligned};
  AUTO.forEach(function(k){if(!S.manual[k])S.ck[k]=auto[k]});
  $("ctxinfo").textContent="تأثير الأخبار على "+asset+" (48 س): "+(ns>0?"+":"")+ns+" | جلسة نيويورك: "+(ny?"دابا":"خارجها")+(S.evtMsg?" | "+S.evtMsg:" | ما كاين حدث قريب");
  ITEMS.forEach(function(i){var c=$("ck_"+i.id);if(c)c.checked=!!S.ck[i.id]});
  calc();
}

function calc(){
  var tot=0,got=0;
  ITEMS.forEach(function(i){tot+=i.w;if(S.ck[i.id])got+=i.w});
  var pct=Math.round(got/tot*100),b=band(pct),block=[],warn=[];
  if(!S.ck.poi)block.push("POI HTF ماكايناش: حسب قاعدتك POI خاصو ديما يكون.");
  else if(!S.ck.poi2)block.push("POI على LTF ماكايناش: ما كاينش تأكيد الدخول.");
  else if(!S.ck.sweep&&!S.ck.smt2)block.push("خاصك معا POI على LTF: sweep ولا SMT.");
  if(num("sl")===null)block.push("حدد الـ SL قبل ما تدخل.");
  if(S.rrInvalid)warn.push("ترتيب Entry / SL / TP ما منطقيش مع الاتجاه.");
  if(S.evtMsg)warn.push(S.evtMsg);
  var col=block.length?"dn":b>=2?"up":b===1?"am":"dn";
  var p=$("pct");p.textContent=pct+"%";p.className="big ltr "+col;
  $("meter").style.width=pct+"%";
  $("meter").className=col;
  var v=$("verdict");
  v.textContent=block.length?"ما تدخلش دابا":"درجة التوافق: "+BANDS[b];
  v.className="verdict "+col;
  $("dockpct").textContent=pct+"%";
  $("dockpct").className="ltr "+col;
  $("dockv").textContent=block.length?"ما تدخلش":BANDS[b];
  var w=$("warns");w.textContent="";
  block.concat(warn).forEach(function(t){w.appendChild(el("div","warn",t))});
  S.last={pct:pct,band:b};
  var closed=jload().filter(function(r){return r.res==="W"||r.res==="L"});
  var same=closed.filter(function(r){return band(r.score)===b});
  var wins=same.filter(function(r){return r.res==="W"}).length;
  $("hist").textContent=same.length
    ?"فصفقاتك السابقة فهاد المستوى ("+BANDS[b]+"): "+Math.round(wins/same.length*100)+"% ربح من "+same.length+" صفقة"+(same.length<20?" (عينة صغيرة، ما تعتمدش عليها بزاف)":"")
    :"ما عندكش صفقات مسجلة فهاد المستوى بعد. سجل نتائج صفقاتك باش تولي عندك نسبة حقيقية.";
}

function saveTrade(){
  var j=jload();
  j.push({ts:Date.now(),asset:$("asset").value,dir:S.dir,score:S.last?S.last.pct:0,rr:$("rrout").textContent,res:null});
  jsave(j);renderJ();calc();
  $("msg").textContent="تسجلات الصفقة. ملي تسالي، حدد النتيجة تحت.";
}
function setRes(i,r){var j=jload();if(j[i]){j[i].res=r;jsave(j);renderJ();calc()}}
function delTrade(i){var j=jload();j.splice(i,1);jsave(j);renderJ();calc()}

function renderJ(){
  var j=jload(),box=$("journal");
  box.textContent="";
  if(!j.length)box.appendChild(el("p","tag","ما كاين حتى صفقة مسجلة."));
  for(var k=j.length-1,c=0;k>=0&&c<15;k--,c++){
    (function(idx){
      var r=j[idx],row=el("div","tr");
      row.appendChild(el("span","ltr",fmt(r.ts)));
      row.appendChild(el("b","ltr",r.asset+" "+(r.dir==="long"?"Long":"Short")));
      row.appendChild(el("span","ltr",r.score+"%"));
      row.appendChild(el("span","ltr",r.rr));
      if(r.res){
        row.appendChild(el("span","res "+(r.res==="W"?"up":r.res==="L"?"dn":"nu"),r.res==="W"?"ربح":r.res==="L"?"خسارة":"BE"));
      }else{
        [["W","ربح"],["L","خسارة"],["B","BE"]].forEach(function(p){
          var bt=el("button","mini",p[1]);
          bt.addEventListener("click",function(){setRes(idx,p[0])});
          row.appendChild(bt);
        });
      }
      var d=el("button","mini x","\u2715");
      d.addEventListener("click",function(){delTrade(idx)});
      row.appendChild(d);
      box.appendChild(row);
    })(k);
  }
  var closed=j.filter(function(r){return r.res==="W"||r.res==="L"});
  var sb=$("stats");
  sb.textContent="";
  if(!closed.length){sb.textContent="الإحصائيات كتبان من بعد ما تسجل نتيجة بعض الصفقات.";return}
  var w=closed.filter(function(r){return r.res==="W"}).length;
  sb.appendChild(el("div","","الإجمالي: "+Math.round(w/closed.length*100)+"% ربح من "+closed.length+" صفقة"));
  BANDS.forEach(function(nm,b){
    var s=closed.filter(function(r){return band(r.score)===b});
    if(!s.length)return;
    var ww=s.filter(function(r){return r.res==="W"}).length;
    sb.appendChild(el("div","tag",nm+": "+Math.round(ww/s.length*100)+"% ربح من "+s.length));
  });
}

function resetAll(){
  S.ck={};S.manual={};
  ["entry","sl","tp"].forEach(function(id){$(id).value=""});
  $("msg").textContent="";
  refresh();
}
function copyData(){
  try{
    navigator.clipboard.writeText(JSON.stringify(jload()));
    $("msg").textContent="تنسخات البيانات. حطها فشي Note باش تحتفظ بيها.";
  }catch(e){$("msg").textContent="ما قدرتش ننسخ."}
}

build();
renderJ();
refresh();
fetch("news.json?t="+Date.now()).then(function(r){return r.json()}).then(function(l){S.news=Array.isArray(l)?l:[];refresh()}).catch(function(){});
fetch("data.json?t="+Date.now()).then(function(r){return r.json()}).then(function(d){S.evts=(d&&d.calendar)||[];refresh()}).catch(function(){});
