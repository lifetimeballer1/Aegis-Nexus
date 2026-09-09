/** Resilient data fetcher with cache + freshness.
 * Guarantees: bounded request timeouts (AbortController), one retry for
 * transient failures, per-feed freshness metadata (state.feedMeta), and
 * batched state updates so a refresh cycle notifies subscribers once.
 * Result shape: {ok, data, fromCache, stale, error, fetchedAt}.
 * stale=true only when cached data is served after a network failure —
 * a within-TTL cache fast-path is NOT stale. Failed feeds without cache
 * preserve the previously loaded data in state (never blanked). */
import { CONFIG } from './config.js';
import { getState, setState, setError, clearError } from './state.js';
const CACHE_PREFIX='gp_cache_'; const CACHE_TTL_MS=30*60*1000;
function cacheKey(url){return CACHE_PREFIX+btoa(url).slice(0,40)}
function getCachedEntry(url){try{const raw=localStorage.getItem(cacheKey(url));if(!raw)return null;const {data,ts}=JSON.parse(raw);if(Date.now()-ts>CACHE_TTL_MS)return null;return{data,ts}}catch{return null}}
function setCached(url,data){try{localStorage.setItem(cacheKey(url),JSON.stringify({data,ts:Date.now()}))}catch{}}
function timeoutFor(label){return label==='snapshot'?CONFIG.fetch.snapshotTimeoutMs:CONFIG.fetch.timeoutMs}
function retriable(err,res){if(res&&Number(res.status)>=500&&Number(res.status)<600)return true;if(err&&(err.name==='AbortError'||err.name==='TimeoutError'))return true;if(err instanceof TypeError)return true;return false}
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function fetchOnce(url,{force,timeoutMs}){
  const ctrl=new AbortController();const timer=setTimeout(()=>ctrl.abort(),timeoutMs);
  try{const res=await fetch(url,{cache:force?'reload':'default',headers:{Accept:'application/json'},signal:ctrl.signal});return{res,err:null}}
  catch(err){return{res:null,err}}
  finally{clearTimeout(timer)}
}
function report(label,ok,message,quiet){if(quiet)return;if(ok)clearError(label);else setError(label,message)}
export async function fetchJson(url,options={}){
  const {force=false,label=url,quiet=false}=options;
  const timeoutMs=options.timeoutMs||timeoutFor(label);
  const retries=options.retries??CONFIG.fetch.retries;
  if(!force){const hit=getCachedEntry(url);if(hit)return{ok:true,data:hit.data,fromCache:true,stale:false,error:null,fetchedAt:new Date(hit.ts).toISOString()}}
  let lastErr=null,lastRes=null;
  for(let attempt=0;attempt<=retries;attempt++){
    const {res,err}=await fetchOnce(url,{force,timeoutMs});
    lastRes=res;lastErr=err;
    if(!err&&res.ok){
      try{
        const data=await res.json();setCached(url,data);report(label,true,null,quiet);
        return{ok:true,data,fromCache:false,stale:false,error:null,fetchedAt:new Date().toISOString()};
      }catch(parseErr){lastErr=parseErr;break}
    }
    if(!retriable(err,res))break;
    if(attempt<retries)await delay(CONFIG.fetch.retryDelayMs);
  }
  const status=lastRes&&!lastRes.ok?`HTTP ${lastRes.status}`:null;
  const message=status||(lastErr&&lastErr.name==='AbortError'?`Request timed out after ${timeoutMs}ms`:(lastErr&&lastErr.message)||'Fetch failed');
  const hit=getCachedEntry(url);
  if(hit){report(label,false,`Using cached data (${message})`,quiet);return{ok:true,data:hit.data,fromCache:true,stale:true,error:message,fetchedAt:new Date(hit.ts).toISOString()}}
  report(label,false,message,quiet);return{ok:false,data:null,fromCache:false,stale:false,error:message,fetchedAt:null};
}
export async function loadCoreData({force=false}={}){
  const prev=getState();
  const cold=!prev.snapshot&&!prev.liveArticles&&!prev.intelligenceGraph;
  if(cold)setState({status:'loading'});
    const urls=[['snapshot',CONFIG.endpoints.snapshot],['liveArticles',CONFIG.endpoints.liveArticles],['intelligenceGraph',CONFIG.endpoints.intelligenceGraph],['intelligenceBrain',CONFIG.endpoints.intelligenceBrain],['sources',CONFIG.endpoints.sources],['sourceHealth',CONFIG.endpoints.sourceHealth],['mapEvents',CONFIG.endpoints.mapEvents],['mapRegional',CONFIG.endpoints.mapRegional],['mapCartel',CONFIG.endpoints.mapCartel],['mapLinks',CONFIG.endpoints.mapLinks],['mapPoints',CONFIG.endpoints.mapPoints],['whatChanged',CONFIG.endpoints.whatChanged],['eventHistory',CONFIG.endpoints.eventHistory],['historicalTrends',CONFIG.endpoints.historicalTrends],['refreshManifest',CONFIG.endpoints.refreshManifest],['intelligenceBrief',CONFIG.endpoints.intelligenceBrief]];
  const results=await Promise.all(urls.map(([label,url])=>fetchJson(url,{force,label,quiet:true})));
  const by=Object.fromEntries(urls.map(([label],i)=>[label,results[i]]));
  const hasAny=by.snapshot.ok||by.liveArticles.ok||by.intelligenceGraph.ok;
  const anyStale=results.some(r=>r.stale);
  const errors={...prev.errors};
  const feedMeta={...prev.feedMeta};
  for(const [label,r] of Object.entries(by)){
    feedMeta[label]={ok:r.ok,fromCache:r.fromCache,stale:r.stale,error:r.error,fetchedAt:r.fetchedAt};
    if(r.ok&&!r.error)delete errors[label];else if(r.error)errors[label]=r.stale?`Using cached data (${r.error})`:r.error;
  }
  const keep=(key,fallback)=>by[key].ok?by[key].data:(fallback??null);
  const prevMap=prev.mapData||{};
  const patch={feedMeta,errors,
    snapshot:by.snapshot.ok?by.snapshot.data:prev.snapshot,
    liveArticles:by.liveArticles.ok?by.liveArticles.data:prev.liveArticles,
    intelligenceGraph:by.intelligenceGraph.ok?by.intelligenceGraph.data:prev.intelligenceGraph,
    intelligenceBrain:by.intelligenceBrain.ok?by.intelligenceBrain.data:prev.intelligenceBrain,
    intelligenceBrief:keep('intelligenceBrief',prev.intelligenceBrief),
    historicalTrends:keep('historicalTrends',prev.historicalTrends),
    refreshManifest:keep('refreshManifest',prev.refreshManifest),
    sources:keep('sources',prev.sources),sourceHealth:keep('sourceHealth',prev.sourceHealth),
    whatChanged:keep('whatChanged',prev.whatChanged),eventHistory:keep('eventHistory',prev.eventHistory),
    mapPoints:by.mapPoints.ok?by.mapPoints.data:prev.mapPoints,
    mapData:{events:by.mapEvents.ok?by.mapEvents.data:prevMap.events,regional:by.mapRegional.ok?by.mapRegional.data:prevMap.regional,cartel:by.mapCartel.ok?by.mapCartel.data:prevMap.cartel,links:by.mapLinks.ok?by.mapLinks.data:prevMap.links},
    lastSuccessfulFetch:hasAny?new Date().toISOString():prev.lastSuccessfulFetch,
    status:hasAny?(anyStale?'stale':'live'):'error'};
  setState(patch);
   return{snapshot:by.snapshot,liveArticles:by.liveArticles,intelligenceGraph:by.intelligenceGraph,intelligenceBrain:by.intelligenceBrain,intelligenceBrief:by.intelligenceBrief,mapPoints:by.mapPoints,mapData:{events:by.mapEvents,regional:by.mapRegional,cartel:by.mapCartel,links:by.mapLinks}};
}
