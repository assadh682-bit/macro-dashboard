var ASSETS=["GC","SIL","NQ","ES","DXY","US10Y","VIX"];
var DUR={instant:"لحظي",daily:"يومي",weekly:"أسبوعي"};
var ARR={up:"\u25b2",down:"\u25bc",neutral:"\u25cf"};
var CLS={up:"up",down:"dn",neutral:"nu"};
var GEO={
"الشرق الأوسط":["middle east","iran","israel","gaza","houthi","red sea","saudi","hormuz","lebanon","syria","yemen"],
"روسيا وأوكرانيا":["russia","ukraine","kremlin","putin","moscow","kyiv"],
"الصين وتايوان":["taiwan","south china sea","beijing"],
"كوريا":["north korea","pyongyang"],
"عقوبات وحرب تجارية":["sanction","tariff","embargo","trade war"]
};
function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}

function ageH(n){return n.ts?Math.max(0,(Date.now()-n.ts)/3600000):null}
function weight(n){
  var h=ageH(n);
  if(h===null)return 0.3;
  if(h>48)return 0;
  return Math.pow(0.5,h/6);
}
function agoText(h){
  if(h<1)return "قبل "+Math.max(1,Math.round(h*60))+" د";
  if(h<24)return "قبل "+Math.round(h)+" س";
  return "قبل "+Math.round(h/24)+" ي";
}

function geo(list){
  var items=list.slice(0,15),sum=0,zones={};
  items.forEach(function(n){
    var t=(n.title||"").toLowerCase(),hit=false;
    Object.keys(GEO).forEach(function(z){
      if(GEO[z].some(function(k){return t.indexOf(k)>-1})){
        hit=true;
        if(!zones[z])zones[z]={c:0,t:n.title||""};
        zones[z].c++;
      }
    });
    if(hit)sum+=(n.importance||2);
  });
  var idx=Math.min(10,Math.round(sum/4));
  var r=document.getElementById("risk");
  r.textContent=idx+" / 10";
  r.className="risk ltr "+(idx>=7?"dn":idx>=4?"am":"up");
  document.getElementById("bar").style.width=(idx*10)+"%";
  var z=document.getElementById("zones"),names=Object.keys(zones);
  if(!names.length){z.appendChild(el("p","tag","ما كاين حتى توتر باين فالأخبار الأخيرة."));return}
  names.sort(function(a,b){return zones[b].c-zones[a].c});
  names.forEach(function(nm){
    var d=el("div","zone");
    d.appendChild(el("b","",nm+" ("+zones[nm].c+") "));
    d.appendChild(el("span","tag ltr",zones[nm].t));
    z.appendChild(d);
  });
}

function render(list){
  var feed=document.getElementById("feed"),score={};
  ASSETS.forEach(function(a){score[a]=0});
  if(!list.length){feed.appendChild(el("p","tag","ما كاين حتى خبر محلل دابا. المنصة كتجيب الأخبار كل ساعة فأيام العمل."))}
  list.forEach(function(n){
    var d=el("div","news"),m=el("div","meta"),w=weight(n),h=ageH(n);
    m.appendChild(el("span","ltr",n.time||""));
    if(h!==null)m.appendChild(el("span","",agoText(h)));
    m.appendChild(el("span","",n.source||""));
    if((n.importance||0)>=4)m.appendChild(el("span","hi","High impact"));
    m.appendChild(el("span","","ثقة AI: "+(n.confidence||0)+"%"));
    d.appendChild(m);
    var b=el("b");
    if(/^https?:/.test(n.link||"")){var a=el("a","",n.title||"");a.href=n.link;a.target="_blank";a.rel="noopener";b.appendChild(a)}
    else b.textContent=n.title||"";
    d.appendChild(b);
    d.appendChild(el("p","",n.summary||""));
    var c=el("div","chips");
    (n.impacts||[]).forEach(function(i){
      var k=i.direction||"neutral";
      var ch=el("span","chip "+(CLS[k]||"nu"));
      ch.appendChild(el("span","ltr",i.asset+" "));
      ch.appendChild(document.createTextNode((ARR[k]||"")+" قوة "+i.strength+"/5 \u00b7 "+(DUR[i.duration]||i.duration)));
      c.appendChild(ch);
      if(score[i.asset]!==undefined)score[i.asset]+=(k==="up"?1:k==="down"?-1:0)*(i.strength||0)*w;
    });
    d.appendChild(c);feed.appendChild(d);
  });
  var hm=document.getElementById("hm");
  ASSETS.forEach(function(a){
    var v=Math.round(score[a]*10)/10,k=v>0?"up":v<0?"dn":"nu",cell=el("div","cell");
    cell.appendChild(el("b","ltr",a));cell.appendChild(el("br"));
    cell.appendChild(el("span",k+" ltr",(v>0?"\u25b2 +":v<0?"\u25bc ":"\u25cf ")+v));
    hm.appendChild(cell);
  });
  geo(list);
  document.getElementById("upd").textContent=list.length?"آخر خبر: "+(list[0].time||"")+" (توقيت المغرب)":"";
}
fetch("news.json?t="+Date.now()).then(function(r){return r.json()}).then(render).catch(function(){
  document.getElementById("feed").appendChild(el("p","tag","ما قدرتش نحمل الأخبار. عاود حدث الصفحة بعد شوية."));
  document.getElementById("upd").textContent="";
});

var EVENTS=[];
function maTime(ts){
  return new Date(ts).toLocaleString("en-GB",{timeZone:"Africa/Casablanca",weekday:"short",day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"});
}
function pad(n){return String(n).padStart(2,"0")}
function tickEv(){
  var now=Date.now(),next=null;
  for(var i=0;i<EVENTS.length;i++){if(EVENTS[i].ts>now){next=EVENTS[i];break}}
  if(!next)return;
  var s=Math.floor((next.ts-now)/1000),d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60),sec=s%60;
  document.getElementById("cd").textContent=(d>0?d+"d ":"")+pad(h)+":"+pad(m)+":"+pad(sec);
}
function renderEvents(d){
  var name=document.getElementById("evname"),list=document.getElementById("evlist");
  if(!d||!d.calendar||!d.calendar.length){
    name.textContent="ما لقيتش بيانات الأحداث دابا.";
    return;
  }
  EVENTS=d.calendar;
  var now=Date.now(),up=EVENTS.filter(function(e){return e.ts>now});
  if(!up.length){name.textContent="ما كاين حتى حدث مهم فالأيام الجاية.";return}
  name.textContent=up[0].title;
  var t="التوقيت بالمغرب: "+maTime(up[0].ts);
  if(up[0].forecast)t+=" | Forecast: "+up[0].forecast;
  if(up[0].previous)t+=" | Previous: "+up[0].previous;
  document.getElementById("evtime").textContent=t;
  up.slice(1,5).forEach(function(e){
    var r=el("div","evrow");
    r.appendChild(el("span","ltr",e.title));
    r.appendChild(el("span","tag ltr",maTime(e.ts)));
    list.appendChild(r);
  });
  tickEv();setInterval(tickEv,1000);
}
fetch("data.json?t="+Date.now()).then(function(r){return r.json()}).then(renderEvents).catch(function(){
  document.getElementById("evname").textContent="ما لقيتش بيانات الأحداث دابا.";
});

var AI_TXT={ok:"Gemini خدام",quota:"حد Gemini وصل",error:"خطأ فـ Gemini",idle:"ما كاين أخبار جديدة"};
function ageText(min){
  if(min<60)return min+" دقيقة";
  var h=Math.floor(min/60);
  return h<24?h+" ساعة":Math.floor(h/24)+" يوم";
}
function inWorkHours(){
  var p=new Intl.DateTimeFormat("en-GB",{timeZone:"Africa/Casablanca",weekday:"short",hour:"2-digit",hour12:false}).formatToParts(new Date());
  var wd="",hr=0;
  p.forEach(function(x){if(x.type==="weekday")wd=x.value;if(x.type==="hour")hr=parseInt(x.value,10)%24});
  return ["Mon","Tue","Wed","Thu","Fri"].indexOf(wd)>-1&&hr>=7&&hr<=21;
}
fetch("status.json?t="+Date.now()).then(function(r){return r.json()}).then(function(s){
  var box=document.getElementById("health");
  var last=new Date(s.last_run).getTime();
  if(isNaN(last))return;
  var min=Math.max(0,Math.floor((Date.now()-last)/60000));
  var txt="آخر تشغيل للبوت: قبل "+ageText(min)+" | "+(AI_TXT[s.ai]||s.ai);
  if(min>180&&inWorkHours()){
    box.className="status bad";
    txt="تنبيه: البوت ما خدمش من "+ageText(min)+". شوف Actions فـ GitHub.";
  }else if(s.ai==="quota"||s.ai==="error"){
    box.className="status bad";
  }
  box.textContent=txt;
}).catch(function(){});
