(()=>{
'use strict';
/*
 * Aegis Nexus Intelligence Web performance guard.
 *
 * This file intentionally does NOT monkey-patch WebGLRenderingContext.
 * Three.js owns WebGL buffer creation and bufferData calls; attempting to
 * identify application buffers by global creation order is unsafe because
 * library initialization order is not a stable API contract and can blank
 * or corrupt the graph renderer.
 *
 * Keep this hook as a harmless compatibility marker so the HTML/runtime can
 * continue loading it without altering the renderer.
 */
if(window.__AEGIS_INTELWEB_PERF__)return;
window.__AEGIS_INTELWEB_PERF__=true;
})();
