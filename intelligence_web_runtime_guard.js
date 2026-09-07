(()=>{'use strict';
const started=performance.now();
const $=id=>document.getElementById(id);
let reported=false;
function show(message,detail){if(reported)return;reported=true;const loading=$('loading');if(!loading)return;loading.style.display='grid';loading.innerHTML=`<div style="padding:18px 22px;max-width:min(520px,calc(100vw - 32px));text-align:center;border:1px solid #193244;border-radius:12px;background:rgba(3,9,15,.96);box-shadow:0 12px 40px #000;color:#8198aa"><strong style="display:block;color:#ff5368;margin-bottom:8px">INTELLIGENCE WEB RUNTIME ERROR</strong><span>${String(message||'Unknown runtime failure').replace(/[&<>\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m])||m)}</span>${detail?`<small style="display:block;margin-top:8px;word-break:break-word">${String(detail).replace(/[&<>\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m])||m)}</small>`:''}</div>`}
function fail(reason,error){show(reason,error&&error.message||error)}
addEventListener('error',e=>{if(e.error)fail('JavaScript initialization failed',e.error);else if(e.message)fail('JavaScript runtime error',e.message)},true);
addEventListener('unhandledrejection',e=>fail('Unhandled asynchronous error',e.reason),true);
const timer=setTimeout(()=>{const loading=$('loading'),stats=$('stats'),canvas=$('gp-canvas');if(loading&&!loading.hidden&&loading.parentNode&&loading.textContent.includes('Loading intelligence graph'))fail('Intelligence graph initialization timed out','No successful graph initialization was observed within 15 seconds.');else if(canvas&&(!canvas.width||!canvas.height))fail('WebGL canvas has no drawable dimensions',`${canvas.width}×${canvas.height}`);else if(stats&&stats.textContent.includes('Preparing intelligence graph'))fail('Graph data did not initialize','The renderer loaded but never populated the intelligence graph.');},15000);
const observer=new MutationObserver(()=>{const canvas=$('gp-canvas');if(canvas&&canvas.width>0&&canvas.height>0)clearTimeout(timer);});
observer.observe(document.documentElement,{subtree:true,childList:true,attributes:true});
window.__AEGIS_INTELWEB_RUNTIME_GUARD__={started,fail};
})();