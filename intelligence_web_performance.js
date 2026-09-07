(()=>{'use strict';
/* Aegis Nexus Intelligence Web — GPU upload guard.
 * The native renderer rebuilds node/link/pulse arrays each frame. Node and link
 * geometry are stable between graph/layout changes, so avoid re-uploading those
 * two GPU buffers when their contents have not changed. Pulse geometry remains
 * intentionally dynamic and is never suppressed.
 */
if(window.__AEGIS_INTELWEB_PERF__)return;
window.__AEGIS_INTELWEB_PERF__=true;
const proto=window.WebGLRenderingContext&&WebGLRenderingContext.prototype;
if(!proto||!proto.bufferData)return;
const original=proto.bufferData;
const originalCreate=proto.createBuffer;
let created=0;
const signatures=new WeakMap();
function signature(data){
  if(!data||typeof data.byteLength!=='number')return '';
  const view=data instanceof ArrayBuffer?new Uint8Array(data):new Uint8Array(data.buffer,data.byteOffset,data.byteLength);
  let h=2166136261;
  for(let i=0;i<view.length;i++){h^=view[i];h=Math.imul(h,16777619)}
  return view.byteLength+':'+(h>>>0);
}
proto.createBuffer=function(){
  const b=originalCreate.apply(this,arguments);
  if(b)b.__aegisIntelBufferIndex=++created;
  return b;
};
proto.bufferData=function(target,data,usage){
  try{
    const bound=this.getParameter(this.ARRAY_BUFFER_BINDING);
    /* buffers 1 and 2 are the renderer's node and relationship geometry.
       Buffer 3 is the animated pulse stream and must upload every frame. */
    if(target===this.ARRAY_BUFFER&&bound&&
       (bound.__aegisIntelBufferIndex===1||bound.__aegisIntelBufferIndex===2)){
      const sig=signature(data);
      if(signatures.get(bound)===sig)return;
      signatures.set(bound,sig);
    }
  }catch(_){/* never interfere with rendering */}
  return original.apply(this,arguments);
};
})();
