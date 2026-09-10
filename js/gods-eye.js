/* Gods-Eye Lite — 2D-first sensor view. Loaded ONLY by gods-eye.html, never index.html.
 * Feeds: USGS all-day quakes (live, sample fallback) + OpenSky states (short timeout, DEMO fallback).
 * Click-to-track + last-N trail polyline on canvas. Optional 3D behind #btn3d via dynamic import. */
(function(){
'use strict';
var cv=document.getElementById('eye'),ctx=cv.getContext('2d');
var hud=document.getElementById('hud'),feedsEl=document.getElementById('feeds');
var detail=document.getElementById('detail'),btn3d=document.getElementById('btn3d');
var mode3d=document.getElementById('mode3d');
var W=cv.width,H=cv.height,TRAIL=12;
/* Bundled tiny quake sample fallback (3 events). */
var QUake_SAMPLE=[{lat:35.7,lon:140.1,mag:5.1,place:'offshore Honshu (sample)',t:Date.now()-36e5},
 {lat:-3.3,lon:128.1,mag:4.6,place:'Banda Sea (sample)',t:Date.now()-72e5},
 {lat:19.4,lon:-155.3,mag:3.2,place:'Hawaii (sample)',t:Date.now()-18e5}];
var quakes=[],flights=[],flightSrc='demo',quakeSrc='sample',tracked=null,threeOn=false;
function eqX(lon){return (lon+180)/360*W}
function eqY(lat){return (90-lat)/180*H}
function fetchJSON(url,ms){var c=new AbortController(),t=setTimeout(function(){c.abort()},ms||7000);
 return fetch(url,{signal:c.signal,cache:'no-store'}).then(function(r){clearTimeout(t);if(!r.ok)throw new Error('http '+r.status);return r.json()}).catch(function(e){clearTimeout(t);throw e})}
function loadQuakes(){
 return fetchJSON('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson',8000).then(function(g){
  var f=(g&&g.features)||[];quakes=f.slice(0,300).map(function(x){var p=x.properties||{},c=(x.geometry||{}).coordinates||[];
   return {lat:c[1],lon:c[0],mag:Number(p.mag)||0,place:p.place||'quake',t:p.time||Date.now()}});
  quakeSrc='live ('+quakes.length+')';
 }).catch(function(){quakes=QUake_SAMPLE.slice();quakeSrc='sample fallback (offline/blocked)'});
}
function demoFlights(){var now=Date.now();return [
 {id:'DEMO-AAL123',lat:39.5,lon:-98.0,h:0,hist:[],demo:true},
 {id:'DEMO-DLH456',lat:50.0,lon:8.0,h:0,hist:[],demo:true},
 {id:'DEMO-SIA789',lat:1.3,lon:103.8,h:0,hist:[],demo:true},
 {id:'DEMO-QFA012',lat:-33.9,lon:151.2,h:0,hist:[],demo:true},
 {id:'DEMO-LAT345',lat:-23.5,lon:-46.6,h:0,hist:[],demo:true}].map(function(f,i){f.h=i;f.t=now;return f})}
function loadFlights(){
 /* OpenSky sample pattern: bounded bbox (CONUS-ish) to keep payload small. */
 var url='https://opensky-network.org/api/states/all?lamin=24&lamax=50&lomin=-126&lomax=-66';
 return fetchJSON(url,6000).then(function(j){
  var st=(j&&j.states)||[];flights=st.slice(0,120).map(function(s){
   return {id:String(s[1]||s[0]||'?').trim()||'UNK',lat:s[6],lon:s[5],h:s[7]||0,hist:[],t:Date.now(),demo:false}});
  flightSrc=flights.length?'live ('+flights.length+')':'live (0 in bbox → +demo)';
  if(!flights.length)flights=demoFlights();
  else flights=flights.concat(demoFlights().slice(0,2));
 }).catch(function(){flights=demoFlights();flightSrc='DEMO fallback (auth/rate-limit/blocked)'});
}
function tickDemo(dt){ /* drift demo flights so trails animate */
 for(var i=0;i<flights.length;i++){var f=flights[i];if(!f.demo)continue;
  f.lon+=dt*1.2;if(f.lon>180)f.lon-=360;f.lat+=Math.sin(Date.now()/9e5+i)*dt*0.25;
  pushHist(f,f.lat,f.lon)}}
function pushHist(f,lat,lon){f.hist.push([lat,lon]);if(f.hist.length>TRAIL)f.hist.shift()}
function drawGrid(){ctx.clearRect(0,0,W,H);ctx.strokeStyle='rgba(90,140,180,.16)';ctx.lineWidth=1;
 for(var lon=-180;lon<=180;lon+=20){var x=eqX(lon);ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke()}
 for(var lat=-90;lat<=90;lat+=20){var y=eqY(lat);ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke()}
 /* world dots: cheap graticule stipple for sensor aesthetic */
 ctx.fillStyle='rgba(110,170,210,.20)';
 for(var yy=10;yy<H;yy+=14)for(var xx=6;xx<W;xx+=14){if((xx+yy)%28<14)ctx.fillRect(xx,yy,1,1)}}
function draw(){
 if(threeOn&&window.__ge3&&window.__ge3.render)return; /* 3D owns the pixels */
 drawGrid();var i,f,x,y;
 /* trails first (under markers) */
 for(i=0;i<flights.length;i++){f=flights[i];if(!f.hist||f.hist.length<2)continue;
  var isT=tracked&&tracked.kind==='flight'&&tracked.ref===f;
  ctx.strokeStyle=isT?'rgba(109,255,168,.9)':'rgba(87,230,255,.35)';ctx.lineWidth=isT?2:1;ctx.beginPath();
  for(var k=0;k<f.hist.length;k++){x=eqX(f.hist[k][1]);y=eqY(f.hist[k][0]);if(k)ctx.lineTo(x,y);else ctx.moveTo(x,y)}
  ctx.stroke()}
 /* quakes */
 for(i=0;i<quakes.length;i++){var q=quakes[i];x=eqX(q.lon);y=eqY(q.lat);var r=2+Math.min(8,(q.mag||0)*1.4);
  ctx.fillStyle=q.mag>=5?'rgba(255,93,93,.9)':'rgba(255,180,84,.85)';ctx.beginPath();ctx.arc(x,y,r,0,7);ctx.fill();
  ctx.strokeStyle='rgba(255,180,84,.25)';ctx.beginPath();ctx.arc(x,y,r+4,0,7);ctx.stroke()}
 /* flights */
 for(i=0;i<flights.length;i++){f=flights[i];if(f.lat==null||f.lon==null)continue;
  x=eqX(f.lon);y=eqY(f.lat);var isT2=tracked&&tracked.kind==='flight'&&tracked.ref===f;
  ctx.fillStyle=isT2?'#6dffa8':(f.demo?'#8a97a5':'#57e6ff');
  ctx.save();ctx.translate(x,y);ctx.rotate(Math.PI/4);ctx.fillRect(-3,-3,6,6);ctx.restore();
  if(isT2){ctx.strokeStyle='#6dffa8';ctx.lineWidth=2;ctx.beginPath();ctx.arc(x,y,10,0,7);ctx.stroke()}}
 /* tracked quake ring */
 if(tracked&&tracked.kind==='quake'){var q2=tracked.ref;x=eqX(q2.lon);y=eqY(q2.lat);
  ctx.strokeStyle='#6dffa8';ctx.lineWidth=2;ctx.beginPath();ctx.arc(x,y,10,0,7);ctx.stroke()}
 var qt=tracked&&tracked.kind==='quake'?'Q':'';
 hud.innerHTML='quakes <b>'+quakes.length+'</b> ('+quakeSrc+') · flights <b>'+flights.length+'</b> ('+flightSrc+')'+(tracked?' · TRACKING '+tracked.label:'');
 try{feedsEl.innerHTML='<div>USGS quakes: <span class="pill '+(quakeSrc.indexOf('live')===0?'live':'err')+'">'+quakeSrc+'</span></div>'
  +'<div>OpenSky: <span class="pill '+(flightSrc.indexOf('live')===0?'live':'demo')+'">'+flightSrc+'</span></div>'
  +'<div style="color:var(--dim)">refresh: quakes 5 min · flights 15 s</div>'}catch(e){}}
function pick(mx,my){var best=null,bd=1e9;
 function consider(kind,ref,lat,lon,label){if(lat==null||lon==null)return;var dx=eqX(lon)-mx,dy=eqY(lat)-my,d=dx*dx+dy*dy;if(d<bd){bd=d;best={kind:kind,ref:ref,label:label}}}
 var i;for(i=0;i<flights.length;i++)consider('flight',flights[i],flights[i].lat,flights[i].lon,flights[i].id);
 for(i=0;i<quakes.length;i++){var q=quakes[i];consider('quake',q,q.lat,q.lon,'M'+(q.mag||'?')+' '+(q.place||''))}
 return bd<900?best:null}
function showDetail(){if(!tracked){detail.textContent='Click a marker to lock + track.';return}
 if(tracked.kind==='flight'){var f=tracked.ref;
  detail.textContent='✈ '+f.id+(f.demo?'\n(DEMO synthetic — clearly labeled)':'\n(live OpenSky state)')+'\nlat '+fmt(f.lat)+' lon '+fmt(f.lon)+'\nalt '+(f.h||0)+' m · trail pts '+f.hist.length;}
 else{var q=tracked.ref;detail.textContent='◉ M'+(q.mag||'?')+' — '+(q.place||'')+'\nlat '+fmt(q.lat)+' lon '+fmt(q.lon)+'\n'+new Date(q.t).toUTCString()}}
function fmt(v){return (v==null||isNaN(v))?'?':Number(v).toFixed(2)}
cv.addEventListener('click',function(e){var r=cv.getBoundingClientRect();
 var mx=(e.clientX-r.left)*W/r.width,my=(e.clientY-r.top)*H/r.height;
 var hit=pick(mx,my);if(hit){tracked=hit;showDetail()}else{tracked=null;showDetail()}draw()});
function refreshFlights(){loadFlights().then(function(){showDetail();draw()}).catch(function(){draw()})}
btn3d.addEventListener('click',function(){
 if(threeOn)return;btn3d.disabled=true;btn3d.textContent='Loading 3D…';
 var t0=performance.now();
 import('https://unpkg.com/three@0.160.0/build/three.module.js').then(function(THREE){
  var ms=performance.now()-t0;
  if(ms>6000){throw new Error('3D load too slow ('+Math.round(ms)+'ms) — staying on 2D')}
  enable3D(THREE);
 }).catch(function(err){btn3d.disabled=false;btn3d.textContent='Enable 3D';
  mode3d.innerHTML='3D unavailable ('+String(err&&err.message||err)+'). Staying on fast 2D canvas.'})});
function enable3D(THREE){
 threeOn=true;
 try{
  var renderer=new THREE.WebGLRenderer({canvas:cv,antialias:false});
  renderer.setSize(W,H,false);
  var scene=new THREE.Scene();scene.background=new THREE.Color(0x04080d);
  var cam=new THREE.PerspectiveCamera(45,W/H,0.1,100);cam.position.set(0,0,3.2);
  var globe=new THREE.Mesh(new THREE.SphereGeometry(1,40,28),
   new THREE.MeshBasicMaterial({color:0x0d2033,wireframe:true,transparent:true,opacity:0.85}));
  scene.add(globe);
  var grp=new THREE.Group();scene.add(grp);
  function ll(lat,lon,r){var phi=(90-lat)*Math.PI/180,th=(lon+180)*Math.PI/180;
   return new THREE.Vector3(-r*Math.sin(phi)*Math.cos(th),r*Math.cos(phi),r*Math.sin(phi)*Math.sin(th))}
  quakes.slice(0,200).forEach(function(q){var m=new THREE.Mesh(new THREE.SphereGeometry(0.008+q.mag*0.002,6,6),
   new THREE.MeshBasicMaterial({color:q.mag>=5?0xff5d5d:0xffb454}));m.position.copy(ll(q.lat,q.lon,1.01));grp.add(m)});
  flights.slice(0,120).forEach(function(f){if(f.lat==null)return;var m=new THREE.Mesh(new THREE.BoxGeometry(0.014,0.014,0.014),
   new THREE.MeshBasicMaterial({color:f.demo?0x8a97a5:0x57e6ff}));m.position.copy(ll(f.lat,f.lon,1.02));grp.add(m)});
  var rot=0,last=performance.now(),frames=0,fpsT=0;
  window.__ge3={render:true};
  (function loop(){if(!threeOn)return;var now=performance.now(),dt=(now-last)/1000;last=now;frames++;fpsT+=dt;
   rot+=dt*0.08;grp.rotation.y=rot;globe.rotation.y=rot;renderer.render(scene,cam);
   if(fpsT>=2){var fps=frames/fpsT;frames=0;fpsT=0;
    if(fps<20){threeOn=false;window.__ge3=null;btn3d.disabled=false;btn3d.textContent='Enable 3D';
     mode3d.textContent='3D auto-disabled: '+Math.round(fps)+' fps < 20 — back on fast 2D.';draw();return}}
   requestAnimationFrame(loop)})();
  btn3d.textContent='3D on';mode3d.textContent='3D globe on (three.js lazy-loaded on click only). 2D canvas remains the default.';
 }catch(err){threeOn=false;btn3d.disabled=false;btn3d.textContent='Enable 3D';
  mode3d.textContent='3D failed ('+String(err&&err.message||err)+'). Staying on 2D.';draw()}
}
/* boot */
drawGrid();hud.textContent='loading feeds…';
Promise.all([loadQuakes(),loadFlights()]).then(function(){showDetail();draw();
 setInterval(refreshFlights,15000);setInterval(loadQuakes,3e5);
 var last=performance.now();
 (function anim(){var now=performance.now(),dt=(now-last)/1000;last=now;tickDemo(dt);showDetail();draw();setTimeout(anim,1000)})();
}).catch(function(){showDetail();draw()});
})();
