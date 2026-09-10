/* Global Pulse — Phase 7 mobile performance layer. */
(function(){
'use strict';
if(window.__GP_PERFORMANCE_V2__)return;
window.__GP_PERFORMANCE_V2__=true;

function idle(fn){
  if('requestIdleCallback' in window) window.requestIdleCallback(fn,{timeout:1200});
  else setTimeout(fn,80);
}

function cacheBust(src){
  try{
    var u=new URL(src,window.location.href);
    u.searchParams.set('gpweb','20260907-runtime2');
    return u.toString();
  }catch(_){
    return src+(src.indexOf('?')>=0?'&':'?')+'gpweb=20260907-runtime2';
  }
}

function lazyIntelWeb(){
  var frame=document.querySelector('.gp-intelweb-frame');
  if(!frame || frame.dataset.gpLazyReady==='1')return;
  frame.dataset.gpLazyReady='1';
  /* Ownership: index.html forces this frame to eager loading at runtime.
     An eager frame is owned by markup — stripping and re-adding src here
     would cancel the eager load and fetch the graph page twice. */
  if(frame.loading==='eager')return;
  var src=frame.getAttribute('src');
  if(!src)return;
  frame.removeAttribute('src');
  var loaded=false;
  var load=function(){
    if(loaded || frame.getAttribute('src'))return;
    loaded=true;
    frame.setAttribute('src',cacheBust(src));
  };

  /* Deep links such as #section-intelweb must never depend on an
     IntersectionObserver callback. They are explicit navigation intent. */
  if(window.location.hash==='#section-intelweb'){
    load();
    return;
  }

  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if(entry.isIntersecting){load();io.disconnect();}
      });
    },{rootMargin:'700px 0px'});
    io.observe(frame);
  }else{
    idle(load);
  }
}

function reduceMotion(){
  if(!window.matchMedia || !window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  var style=document.createElement('style');
  style.id='gp-reduced-motion';
  style.textContent='*,*::before,*::after{scroll-behavior:auto!important;animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important}';
  document.head.appendChild(style);
}

function deferBelowFold(){
  var sections=[].slice.call(document.querySelectorAll('.gp-section'));
  if(!sections.length || !('contentVisibility' in document.documentElement.style))return;
  sections.forEach(function(section,i){
    if(i<2)return;
    section.style.contentVisibility='auto';
    section.style.containIntrinsicSize='auto 600px';
  });
}

function mark(){
  try{performance.mark('global-pulse-performance-ready');}catch(_){ }
}

function boot(){
  lazyIntelWeb();
  reduceMotion();
  idle(function(){deferBelowFold();mark();});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});
else boot();
})();
