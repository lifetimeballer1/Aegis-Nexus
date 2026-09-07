(()=>{
'use strict';
function install(){
  const toggle=document.getElementById('control-toggle');
  const controls=document.getElementById('controls');
  if(!toggle||!controls||toggle.dataset.gpControlsFix==='1')return;
  toggle.dataset.gpControlsFix='1';
  const setOpen=open=>{
    controls.classList.toggle('collapsed',!open);
    toggle.classList.toggle('active',open);
    toggle.setAttribute('aria-expanded',String(open));
    toggle.textContent=open?'☰ CLOSE FILTERS':'☰ OPEN FILTERS';
  };
  toggle.addEventListener('click',e=>{
    e.preventDefault();
    e.stopImmediatePropagation();
    setOpen(controls.classList.contains('collapsed'));
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&!controls.classList.contains('collapsed'))setOpen(false);
  });
  setOpen(true);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();
