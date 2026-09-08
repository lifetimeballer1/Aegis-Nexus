/** Resilient data fetcher with cache + freshness */
import { CONFIG } from './config.js';
import { setState, setError, clearError } from './state.js';
const CACHE_PREFIX='gp_cache_'; const CACHE_TTL_MS=30*60*1000;
function cacheKey(url){return CACHE_PREFIX+btoa(url).slice(0,40)}
function getCached(url){try{const raw=localStorage.getItem(cacheKey(url));if(!raw)return null;const {data,ts}=JSON.parse(raw);if(Date.now()-ts>CACHE_TTL_MS)return null;return data}catch{return null}}
function setCached(url,data){try{localStorage.setItem(cacheKey(url),JSON.stringify({data,ts:Date.now()}))}catch{}}
export async function fetchJson(url,options={}){const {force=false,label=url}=options;if(!force){const cached=getCached(url);if(cached)return{ok:true,data:cached,fromCache:true,error:null}}try{const res=await fetch(url,{cache:force?'reload':'default',headers:{Accept:'application/json'}});if(!res.ok)throw new Error(`HTTP ${res.status}`);const data=await res.json();setCached(url,data);clearError(label);return{ok:true,data,fromCache:false,error:null}}catch(err){const cached=getCached(url);if(cached){setError(label,`Using cached data (${err.message})`);return{ok:true,data:cached,fromCache:true,error:err.message}}setError(label,err.message||'Fetch failed');return{ok:false,data:null,fromCache:false,error:err.message}}}
export async function loadCoreData({force=false}={}){
 setState({status:'loading'});
  const urls=[['snapshot',CONFIG.endpoints.snapshot],['liveArticles',CONFIG.endpoints.liveArticles],['intelligenceGraph',CONFIG.endpoints.intelligenceGraph],['sources',CONFIG.endpoints.sources],['sourceHealth',CONFIG.endpoints.sourceHealth],['mapEvents',CONFIG.endpoints.mapEvents],['mapRegional',CONFIG.endpoints.mapRegional],['mapCartel',CONFIG.endpoints.mapCartel],['mapLinks',CONFIG.endpoints.mapLinks],['whatChanged',CONFIG.endpoints.whatChanged]];
 const results=await Promise.all(urls.map(([label,url])=>fetchJson(url,{force,label})));
 const by=Object.fromEntries(urls.map(([label],i)=>[label,results[i]]));
 const hasAny=by.snapshot.ok||by.liveArticles.ok||by.intelligenceGraph.ok;
  setState({snapshot:by.snapshot.data,liveArticles:by.liveArticles.data,intelligenceGraph:by.intelligenceGraph.data,sources:by.sources.data,sourceHealth:by.sourceHealth.data,whatChanged:by.whatChanged.data,mapData:{events:by.mapEvents.data,regional:by.mapRegional.data,cartel:by.mapCartel.data,links:by.mapLinks.data},lastSuccessfulFetch:hasAny?new Date().toISOString():null,status:hasAny?(by.snapshot.fromCache||by.liveArticles.fromCache?'stale':'live'):'error'});
 return{snapshot:by.snapshot,liveArticles:by.liveArticles,intelligenceGraph:by.intelligenceGraph,mapData:{events:by.mapEvents,regional:by.mapRegional,cartel:by.mapCartel,links:by.mapLinks}};
}
