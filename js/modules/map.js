/** Global Situation Map — canonical marker renderer. */
import { getState } from '../core/state.js';
import { CONFIG } from '../core/config.js';
import { escapeHtml } from '../core/utils.js';
import { fetchJson } from '../core/fetch.js';

let map=null;
let groups={};
let brainLinks=null;
let mapData=null;
let selected=null;
let query='';
let filter='all';
const LAYERS={conflicts:{label:'Conflicts & Military',color:'#ff405f',icon:'⚔️'},hazards:{label:'Hazards & Disasters',color:'#ffd34d',icon:'⚠️'},strategic:{label:'Strategic Sites',color:'#4d9aff',icon:'🎯'},cartel:{label:'Cartel / Organized Crime',color:'#ff8a35',icon:'🕶️'},osint:{label:'OSINT / Reporting',color:'#b08cff',icon:'🛰️'}};
let enabled=Object.fromEntries(Object.keys(LAYERS).map(k=>[k,true]));
let showBrainLinks=true;
try{Object.assign(enabled,JSON.parse(localStorage.getItem('gp.mapLayers')||'{}'));filter=localStorage.getItem('gp.mapFilter')||'all';showBrainLinks=localStorage.getItem('gp.mapBrainLinks')!=='0'}catch{}
const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
function coords(x){
  if(!x||typeof x!=='object')return null;
  let lat=num(x.lat??x.latitude??x.lat_deg??x.coordinates?.lat??x.location?.lat??x.location?.latitude);
  let lon=num(x.lng??x.lon??x.longitude??x.long??x.coordinates?.lon??x.location?.lon??x.location?.longitude);
  if((lat==null||lon==null)&&Array.isArray(x.coordinates)&&x.coordinates.length>=2){lon=num(x.coordinates[0]);lat=num(x.coordinates[1])}
  if((lat==null||lon==null)&&Array.isArray(x.geometry?.coordinates)&&x.geometry.coordinates.length>=2){lon=num(x.geometry.coordinates[0]);lat=num(x.geometry.coordinates[1])}
  return lat!=null&&lon!=null&&Math.abs(lat)<=90&&Math.abs(lon)<=180?[lat,lon]:null;
}
function flatten(value,source,out=[],seen=new WeakSet(),depth=0){
  if(value==null||typeof value!=='object'||depth>12||seen.has(value))return out;
  seen.add(value);
  if(Array.isArray(value)){for(const v of value)flatten(v,source,out,seen,depth+1);return out}
  const c=coords(value);if(c)out.push({...value,__lat:c[0],__lon:c[1],__source:source});
  for(const [k,v] of Object.entries(value))if(v&&typeof v==='object')flatten(v,source||k,out,seen,depth+1);
  return out;
}
function classify(p){
  const s=[p.layer,p.type,p.eventType,p.category,p.signal,p.sourceType,p.group,p.kind,p.title,p.name,p.detail,p.description,p.__source].filter(Boolean).join(' ').toLowerCase();
  if(/cartel|organized.?crime|narco|enforcer|gang/.test(s))return'cartel';
  if(/hazard|gdacs|earthquake|wildfire|flood|cyclone|hurricane|storm|landslide|drought|disaster/.test(s))return'hazards';
  if(/strategic|chokepoint|military.?base|infrastructure|flashpoint|strategic site/.test(s))return'strategic';
  if(/osint|regional intelligence|reporting|source|news|article/.test(s))return'osint';
  return'conflicts';
}
function unique(points){const seen=new Set();return points.filter(p=>{const key=String(p.id??p.nodeId??p.eventId??p.mapId??p.datasetEventId??p.sourceUrl??p.url??`${p.__lat.toFixed(4)},${p.__lon.toFixed(4)},${p.title??p.name??p.location??''}`);if(seen.has(key))return false;seen.add(key);return true})}
let collectCache={fp:'',points:[]};
function collect(){
  const s0=getState()||{};
  const fp0=JSON.stringify([s0.snapshot?.updatedAt,s0.mapPoints?.updatedAt,mapData?.snapshot?.updatedAt,mapData?.events?.updatedAt,mapData?.regional?.updatedAt,mapData?.cartel?.updatedAt,mapData?.links?.updatedAt,mapData?.points?.updatedAt,mapData?.brain?.updatedAt]);
  if(collectCache.fp===fp0)return collectCache.points;
  const s=s0;const sources=[];
  const add=(name,data)=>{if(data&&typeof data==='object')sources.push([name,data])};
  add('snapshot',s.snapshot);add('snapshot-markers',s.snapshot?.markers);add('snapshot-osint',s.snapshot?.osintMaps);add('snapshot-conflict',s.snapshot?.conflictDataset);add('snapshot-map',s.snapshot?.mapPoints);
  add('canonical-points',s.mapPoints);add('canonical-markers',s.mapPoints?.markers);
  add('state-events',s.mapData?.events);add('state-regional',s.mapData?.regional);add('state-cartel',s.mapData?.cartel);add('state-links',s.mapData?.links);add('state-points',s.mapData?.points);
  add('live-snapshot',mapData?.snapshot);add('live-events',mapData?.events);add('live-regional',mapData?.regional);add('live-cartel',mapData?.cartel);add('live-links',mapData?.links);add('live-points',mapData?.points);
  const brain=mapData?.brain;
  if(brain?.sourceBackedOnly===true&&Array.isArray(brain.nodes))add('intelligence-brain',brain.nodes.filter(n=>coords(n)).map(n=>({...n,nodeId:String(n.id),brainNode:true,detail:n.description||n.summary||`${n.mentions||0} mentions · ${n.evidence?.length||0} evidence records`})));
  const points=unique(sources.flatMap(([name,data])=>flatten(data,name)));collectCache={fp:fp0,points};return points;
}
function brainEdgesFor(p){
  const brain=mapData?.brain;if(!brain||!Array.isArray(brain.edges))return[];
  const id=String(p.nodeId??p.id??'');if(!id)return[];
  const byId=new Map((brain.nodes||[]).map(n=>[String(n.id),n]));
  return brain.edges.filter(e=>String(e.source)===id||String(e.target)===id).slice(0,8).map(e=>{
    const other=String(e.source)===id?byId.get(String(e.target)):byId.get(String(e.source));
    return {id:String(other?.id||''),label:other?.label||'Connected intelligence',relationship:e.relationship||e.label||e.type||'contextual relationship',evidence:e.evidence?.[0]||null};
  });
}
function renderBrainLinks(){
  if(!brainLinks)return;
  brainLinks.clearLayers();
  if(!showBrainLinks)return;
  const brain=mapData?.brain;if(brain?.sourceBackedOnly!==true||!Array.isArray(brain.nodes)||!Array.isArray(brain.edges))return;
  const byId=new Map();brain.nodes.forEach(n=>{const c=coords(n);if(c)byId.set(String(n.id),c)});
  for(const e of brain.edges){const a=byId.get(String(e.source)),b=byId.get(String(e.target));if(!a||!b||String(e.source)===String(e.target))continue;
    const line=L.polyline([a,b],{pane:'gp-brain-links',color:'#8da2c4',weight:1.5,opacity:.55,dashArray:'5 6',interactive:false});
    line.bindTooltip(String(e.relationship||e.label||e.type||'Intelligence relationship').slice(0,100),{sticky:true});
    brainLinks.addLayer(line);
  }
}
function matches(p){const k=classify(p);if(!enabled[k])return false;if(filter!=='all'&&filter!==k&&!(filter==='conflict'&&k==='conflicts'))return false;if(!query)return true;return [p.title,p.name,p.location,p.country,p.region,p.city,p.detail,p.summary,p.description,p.source,p.type,p.layer,p.eventType,p.kind,p.nodeId].map(v=>String(v??'').toLowerCase()).join(' ').includes(query)}
function controls(){
  const host=document.getElementById('mapContainer')?.parentElement;if(!host||document.getElementById('gpMapControls'))return;
  const box=document.createElement('div');box.id='gpMapControls';box.className='gp-map-mymaps-controls';
  box.innerHTML=`<div class="gp-map-toolbar"><button class="gp-map-tool" id="gpMapLayers" aria-expanded="false" aria-controls="gpMapLayerPanel">☰ Layers</button><button class="gp-map-tool" id="gpMapFit">◎ Fit all</button><button class="gp-map-tool" id="gpMapReset">↺ Reset</button><input id="gpMapSearch" class="gp-map-search" type="search" aria-label="Search map signals" placeholder="Search places, events, countries…"><span id="gpMapCount" class="gp-map-count">0 signals</span></div><div id="gpMapLayerPanel" class="gp-map-layers-panel"><strong>MAP LAYERS</strong><div id="gpMapLayerRows"></div><label class="gp-map-layer-row"><input type="checkbox" id="gpMapBrainLinks" ${showBrainLinks?'checked':''}><span class="gp-map-layer-dot" style="background:#8da2c4"></span><span>🧠 Brain relationships</span><b id="gpMapBrainLinkCount">0</b></label></div>`;
  host.insertBefore(box,document.getElementById('mapContainer'));const rows=box.querySelector('#gpMapLayerRows');
  for(const [k,m] of Object.entries(LAYERS)){const label=document.createElement('label');label.className='gp-map-layer-row';label.innerHTML=`<input type="checkbox" data-layer-check="${k}" ${enabled[k]?'checked':''}><span class="gp-map-layer-dot" style="background:${m.color}"></span><span>${m.icon} ${m.label}</span><b id="gpMapLayerCount-${k}">0</b>`;rows.appendChild(label);label.querySelector('input').onchange=e=>{enabled[k]=e.target.checked;localStorage.setItem('gp.mapLayers',JSON.stringify(enabled));renderMap();renderMapOps()}}
  const layersBtn=box.querySelector('#gpMapLayers');
  layersBtn.onclick=()=>{const panel=box.querySelector('#gpMapLayerPanel');const open=panel.classList.toggle('open');layersBtn.setAttribute('aria-expanded',open?'true':'false')};
  box.querySelector('#gpMapFit').onclick=fitAll;box.querySelector('#gpMapReset').onclick=()=>{query='';filter='all';enabled=Object.fromEntries(Object.keys(LAYERS).map(k=>[k,true]));showBrainLinks=true;localStorage.removeItem('gp.mapLayers');localStorage.removeItem('gp.mapFilter');localStorage.removeItem('gp.mapBrainLinks');box.querySelector('#gpMapSearch').value='';box.querySelectorAll('[data-layer-check]').forEach(x=>x.checked=true);box.querySelector('#gpMapBrainLinks').checked=true;renderMap();renderMapOps();fitAll()};
  const mapSearch=box.querySelector('#gpMapSearch');
  mapSearch.oninput=()=>{query=mapSearch.value.trim().toLowerCase();renderMap();renderMapOps();const again=document.getElementById('gpMapSearch');if(again){again.focus();again.setSelectionRange(again.value.length,again.value.length)}};
  box.querySelector('#gpMapBrainLinks').onchange=e=>{showBrainLinks=e.target.checked;localStorage.setItem('gp.mapBrainLinks',showBrainLinks?'1':'0');renderBrainLinks()};
}
function makeGroup(){
  if(typeof L.markerClusterGroup!=='function')return L.layerGroup();
  return L.markerClusterGroup({
    pane:'gp-signals',
    chunkedLoading:true,
    chunkInterval:80,
    chunkDelay:20,
    maxClusterRadius:55,
    disableClusteringAtZoom:7,
    spiderfyOnMaxZoom:true,
    showCoverageOnHover:false,
    zoomToBoundsOnClick:true,
    animate:true,
    animateAddingMarkers:false,
    /* M4 — clusters wear their dominant child layer color so a conflict
     * cluster never looks like an OSINT cluster. Falls back to neutral. */
    iconCreateFunction(cluster){
      const kids=cluster.getAllChildMarkers();
      const votes={};
      for(const m of kids){const k=m.options?.__layer;if(k)votes[k]=(votes[k]||0)+1}
      let top=null,topN=0;
      for(const [k,n] of Object.entries(votes)){if(n>topN){topN=n;top=k}}
      const color=(top&&LAYERS[top]?LAYERS[top].color:'#8da2c4');
      const n=cluster.getChildCount();
      const size=n<10?'small':n<100?'medium':'large';
      return L.divIcon({html:'<div style="background:'+color+'"><span>'+n+'</span></div>',className:'marker-cluster marker-cluster-'+size,iconSize:L.point(40,40)});
    }
  });
}
export function initMap(){
  const el=document.getElementById('mapContainer');
  if(!el||map||typeof L==='undefined')return;
  map=L.map(el,{center:CONFIG.mapDefaultCenter,zoom:CONFIG.mapDefaultZoom,worldCopyJump:true,preferCanvas:true,zoomControl:true});
  map.createPane('gp-brain-links').style.zIndex='430';map.createPane('gp-signals').style.zIndex='650';
  /* Dark operational basemap (keyless Esri dark-gray canvas; CARTO now requires an API key) + OSM fallback for offline/CSP */
  const dark=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'© Esri © OpenStreetMap contributors'});
  const osm=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'});
  dark.addTo(map);
  dark.on('tileerror',()=>{try{if(!map.hasLayer(osm))osm.addTo(map);}catch{}});
  brainLinks=L.layerGroup().addTo(map);
  for(const k of Object.keys(LAYERS)){groups[k]=makeGroup();groups[k].addTo(map)}
  controls();ensureMapSize();map.on('click',closeDetail);document.addEventListener('keydown',e=>{if(e.key==='Escape'){const p=document.getElementById('mapSidePanel');if(p&&p.style.display!=='none')closeDetail()}});
}
/* M1 — the map section renders below the fold under content-visibility,
 * so the container can measure 0px wide at boot (zero-size canvas =
 * invisible, unclickable markers). Revalidate size until real, and again
 * whenever the section scrolls into view. */
let sizeChecks=0;
function ensureMapSize(){
  if(!map)return;
  const el=document.getElementById('mapContainer');
  const retry=()=>{
    if(!map||sizeChecks>40)return;sizeChecks++;
    const r=el?.getBoundingClientRect();
    if(r&&r.width>0){
      try{map.invalidateSize();}catch{}
      if(map.getSize().x>0){
        /* Force a full view reset so canvas renderers recompute bounds
         * (invalidateSize alone does not resize already-created canvases
         * when the size value itself did not change). */
        try{map.setView(map.getCenter(),map.getZoom(),{animate:false});}catch{}
        renderMap();return;
      }
    }
    setTimeout(retry,250);
  };
  setTimeout(retry,100);
  if(!ensureMapSize._observed&&typeof IntersectionObserver!=='undefined'&&el){
    ensureMapSize._observed=true;
    const io=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting){sizeChecks=0;retry();}});},{rootMargin:'200px 0px'});
    io.observe(el);
  }
}
async function getFeed(key){try{const base=CONFIG.endpoints[key];if(!base)return null;const r=await fetchJson(base,{label:'map-'+key,quiet:true,retries:1});return r.ok?r.data:null}catch{return null}}
export async function loadMapData(){
  const s=getState()||{};
  const obj=v=>(v&&typeof v==='object')?v:null;
  mapData={snapshot:obj(s.snapshot),events:obj(s.mapData?.events),regional:obj(s.mapData?.regional),cartel:obj(s.mapData?.cartel),links:obj(s.mapData?.links),points:obj(s.mapPoints),brain:obj(s.intelligenceBrain)};
  const missing=[];
  if(!mapData.snapshot)missing.push(['snapshot','snapshot']);
  if(!mapData.events)missing.push(['events','mapEvents']);
  if(!mapData.regional)missing.push(['regional','mapRegional']);
  if(!mapData.cartel)missing.push(['cartel','mapCartel']);
  if(!mapData.links)missing.push(['links','mapLinks']);
  if(!mapData.points)missing.push(['points','mapPoints']);
  if(!mapData.brain)missing.push(['brain','intelligenceBrain']);
  if(missing.length){
    const rs=await Promise.all(missing.map(([,ep])=>fetchJson(CONFIG.endpoints[ep],{label:'map-'+ep,quiet:true,retries:1})));
    missing.forEach(([k],i)=>{if(rs[i].ok)mapData[k]=rs[i].data});
  }
  renderMap();return mapData;
}
/* M2 — fingerprint of everything the marker build depends on. Re-renders
 * are skipped when nothing changed, so background state updates (other
 * workspaces, fetch telemetry) no longer rebuild ~3k markers + clusters
 * and flicker the map under the user's cursor. */
const MAP_RENDER_CAP=5000;
function renderFingerprint(){
  const s=getState()||{};
  return JSON.stringify([s.mapPoints?.updatedAt,s.snapshot?.updatedAt,mapData?.snapshot?.updatedAt,mapData?.events?.updatedAt,mapData?.regional?.updatedAt,mapData?.cartel?.updatedAt,mapData?.links?.updatedAt,mapData?.points?.updatedAt,mapData?.brain?.updatedAt,filter,query,enabled,showBrainLinks]);
}
export function renderMap(){
  if(!map)initMap();if(!map)return;
  const fp=renderFingerprint();
  if(fp===renderMap._fp&&renderMap._fitted)return;
  renderMap._fp=fp;
  for(const g of Object.values(groups))g.clearLayers();renderBrainLinks();
  const all=collect();const capped=all.length>MAP_RENDER_CAP;const points=all.filter(matches).slice(0,MAP_RENDER_CAP);const counts=Object.fromEntries(Object.keys(LAYERS).map(k=>[k,0]));
  for(const p of points){const k=classify(p);counts[k]++;const m=LAYERS[k];const imp=Math.max(1,Math.min(3,Number(p.importance)||1));const marker=L.circleMarker([p.__lat,p.__lon],{pane:'gp-signals',radius:p.brainNode?10:6+imp,color:'#ffffff',weight:2.5,fillColor:m.color,fillOpacity:.98,opacity:1,interactive:true,__layer:k});marker.__point=p;marker.bindTooltip(String(p.title||p.label||p.name||p.location||m.label).slice(0,120),{direction:'top',sticky:true});marker.on('click',e=>{/* M1 — stop BOTH propagation layers: native stopPropagation blocks DOM bubble to the container's own click handler, and _stopped halts Leaflet's internal target loop before it reaches map.on('click',closeDetail), which would otherwise close the panel in the same tick. */if(e.originalEvent){e.originalEvent._stopped=true;try{e.originalEvent.stopPropagation();}catch{}}highlightMarker(marker);showDetail(p)});groups[k].addLayer(marker)}
  const total=all.length;const shown=points.length;const count=document.getElementById('gpMapCount');if(count)count.textContent=capped?`${shown.toLocaleString()} of ${total.toLocaleString()} signals (cap)`:`${total.toLocaleString()} signals`;
  for(const k of Object.keys(LAYERS)){const e=document.getElementById(`gpMapLayerCount-${k}`);if(e)e.textContent=counts[k].toLocaleString()}
  const linkCount=document.getElementById('gpMapBrainLinkCount');if(linkCount){const brain=mapData?.brain;let drawn=0;if(Array.isArray(brain?.edges)&&Array.isArray(brain?.nodes)){const withCoords=new Set(brain.nodes.filter(n=>coords(n)).map(n=>String(n.id)));drawn=brain.edges.filter(e=>String(e.source)!==String(e.target)&&withCoords.has(String(e.source))&&withCoords.has(String(e.target))).length}linkCount.textContent=String(drawn)}
  /* M1 — auto-fit only on the first render with data. Background refreshes
   * re-render markers in place; refitting every time would yank the user's
   * zoom/pan (and rebuild clusters under their cursor). Fit/Reset buttons
   * still fit explicitly. */
  if(total&&!renderMap._fitted){renderMap._fitted=true;fitAll(points)}
  else if(!total)setTimeout(()=>map.invalidateSize(),50)
}
function fitAll(points=collect().filter(matches)){if(!map||!points.length)return;map.fitBounds(L.latLngBounds(points.map(p=>[p.__lat,p.__lon])).pad(.08),{maxZoom:4,animate:false})}
function closeDetail(){const p=document.getElementById('mapSidePanel');if(p){p.style.display='none';p.innerHTML=''}if(selectedMarker){try{const s=selectedMarker.__point||{};selectedMarker.setStyle({radius:(s.brainNode?10:6+Math.max(1,Math.min(3,Number(s.importance)||1))),weight:2.5,fillOpacity:.98})}catch{}selectedMarker=null}selected=null}
let selectedMarker=null;
function highlightMarker(marker){try{if(selectedMarker&&selectedMarker!==marker){const s=selectedMarker.__point||{};selectedMarker.setStyle({radius:(s.brainNode?10:6+Math.max(1,Math.min(3,Number(s.importance)||1))),weight:2.5,fillOpacity:.98})}selectedMarker=marker;if(marker){marker.setStyle({radius:12,weight:4,color:'#ffffff',fillOpacity:1});if(marker.bringToFront)marker.bringToFront()}}catch{}}
function linkedEvent(p){const links=Array.isArray(mapData?.links?.links)?mapData.links.links:[];if(!links.length)return null;const id=p.eventId||p.datasetEventId;if(id){const hit=links.find(l=>String(l.eventId)===String(id));if(hit)return hit}let best=null,bd=0.06;for(const l of links){const d=Math.hypot(Number(l.lat)-p.__lat,Number(l.lng)-p.__lon);if(Number.isFinite(d)&&d<bd){bd=d;best=l}}return best}
function detailField(label,value){return value?`<div class="gp-map-detail-field"><b>${escapeHtml(label)}</b><span>${escapeHtml(String(value))}</span></div>`:''}
function showDetail(p){closeDetail();selected=p;const selKey=String(p.nodeId??p.id??p.eventId??'');document.querySelectorAll('.gp-map-op-row').forEach(r=>r.classList.toggle('selected',!!selKey&&r.dataset.mapOpsFocus===selKey));const panel=document.getElementById('mapSidePanel');if(!panel)return;const k=classify(p),m=LAYERS[k],title=p.title||p.label||p.name||p.location||'Map signal',detail=p.detail||p.summary||p.description||p.reason||'No additional detail available.',url=p.url||p.sourceUrl||p.source_url||'',links=brainEdgesFor(p),linked=linkedEvent(p);const conf=p.confidence||p.verification||'',imp=Number.isFinite(Number(p.importance))?Number(p.importance):null,etype=p.eventType||p.type||p.layer||'',srcCount=Array.isArray(p.sources)?p.sources.length:(Number(p.sourceCount)||null),fresh=Number.isFinite(Number(p.freshnessMinutes))?`${Number(p.freshnessMinutes).toFixed(0)} min`:'',precision=/unverified|not an exact|approximate|preliminary|source map report/i.test(`${conf} ${p.type||''} ${detail}`)?'Approximate / source-reported position':'';const fields=detailField('Confidence',conf)+detailField('Importance',imp!=null?imp:'')+detailField('Event type',etype)+detailField('Freshness',fresh)+detailField('Source records',srcCount!=null?srcCount:'')+detailField('Geo precision',precision);panel.style.display='block';panel.style.borderLeft='3px solid '+m.color;panel.innerHTML=`<div class="gp-map-detail-head"><span aria-hidden="true">${m.icon}</span><div><div class="gp-card-title">${escapeHtml(title)}</div><div class="gp-map-detail-type">${escapeHtml(m.label)}${p.brainNode?' · Intelligence Brain':''}</div></div><button id="gpMapClose" class="gp-btn" type="button" aria-label="Close signal details">×</button></div><div class="gp-map-detail-coords">${p.__lat.toFixed(4)}, ${p.__lon.toFixed(4)} <button id="gpMapCopyCoords" class="gp-btn" type="button" style="margin-left:6px;min-height:28px;padding:2px 8px;font-size:10px">Copy</button></div>${fields?`<div class="gp-map-detail-fields">${fields}</div>`:''}<div class="gp-map-detail-text">${escapeHtml(String(detail).slice(0,1400))}</div><div class="gp-map-detail-note">Marker color encodes map layer and size encodes recorded importance; neither is a risk judgement.</div>${p.source?`<div class="gp-map-detail-source">Source: ${escapeHtml(p.source)}</div>`:''}${srcCount?`<div class="gp-map-detail-source">${srcCount} source record${srcCount===1?'':'s'} attached to this signal.</div>`:''}${linked?`<div class="gp-map-detail-source"><strong>Linked event (candidate match, unverified)</strong><div style="margin-top:4px">${escapeHtml(String(linked.eventTitle||'Event').slice(0,200))}</div><div class="gp-map-detail-note">Match confidence: ${escapeHtml(String(linked.confidence||'candidate'))}${Number.isFinite(Number(linked.matchScore))?` · score ${Number(linked.matchScore).toFixed(2)}`:''}</div></div>`:''}${links.length?`<div class="gp-map-detail-source"><strong>Brain connections</strong>${links.map(x=>`<div style="margin-top:6px"><button type="button" class="gp-map-brain-link" data-brain-target="${escapeHtml(x.id)}" style="background:none;border:0;padding:0;color:inherit;text-align:left;cursor:pointer">${escapeHtml(x.label)} — ${escapeHtml(x.relationship)}</button></div>`).join('')}<div class="gp-map-detail-note">Contextual evidence links from the canonical Brain graph; not proof of causation.</div></div>`:''}<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap"><button id="gpMapOpenBrain" class="gp-btn" type="button">Open in Brain</button><button id="gpMapOpenWeb" class="gp-btn" type="button">Open in Web</button>${/^https?:\/\//i.test(String(url))?`<a class="gp-btn" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>`:''}</div>`;panel.querySelector('#gpMapClose').onclick=closeDetail;panel.querySelector('#gpMapCopyCoords')?.addEventListener('click',()=>{const text=`${p.__lat.toFixed(4)}, ${p.__lon.toFixed(4)}`;const done=()=>{const b=panel.querySelector('#gpMapCopyCoords');if(b)b.textContent='Copied'};try{navigator.clipboard.writeText(text).then(done,done)}catch{done()}});panel.querySelector('#gpMapOpenBrain')?.addEventListener('click',()=>{const id=p.nodeId||p.id||'';if(id)window.dispatchEvent(new CustomEvent('gp:brain-select',{detail:{id:String(id),label:title,source:'map'}}));document.getElementById('brainBody')?.scrollIntoView({behavior:'smooth',block:'start'})});panel.querySelector('#gpMapOpenWeb')?.addEventListener('click',()=>{window.dispatchEvent(new CustomEvent('gp:brain-select',{detail:{id:String(p.nodeId||p.id||''),label:title,source:'map'}}));try{window.location.hash='#section-intelweb'}catch{}});panel.querySelectorAll('[data-brain-target]').forEach(btn=>btn.onclick=()=>{const id=btn.dataset.brainTarget;if(!id)return;window.dispatchEvent(new CustomEvent('gp:brain-select',{detail:{id,source:'map'}}));document.getElementById('brainBody')?.scrollIntoView({behavior:'smooth',block:'start'});closeDetail()});if(p.brainNode&&p.nodeId)window.dispatchEvent(new CustomEvent('gp:brain-select',{detail:{id:String(p.nodeId),source:'map'}}));try{panel.querySelector('#gpMapClose')?.focus()}catch{}}
/* GUI Phase 3 — Geospatial Operations workspace.
 * Reads the canonical validated feed (state.mapPoints / data/map_points.json
 * with markers, updatedAt, count) plus live map layers. Layer counts are real
 * counts from the same collect() pipeline that drives Leaflet markers, so the
 * operations list never disagrees with the rendered map. Nothing is
 * fabricated: missing data renders honest loading/empty states. Severity
 * follows the shared language (critical/watch/info/healthy), never
 * decoration. */
const OPS_LAYERS=['conflicts','hazards','strategic','cartel','osint'];
const OPS_MAX_ROWS=30;
function normalizeOpsFilter(value){
  const v=String(value||'all').toLowerCase();
  if(v==='all')return'all';
  if(v==='conflict'||v==='conflicts')return'conflicts';
  if(v==='hazard'||v==='hazards')return'hazards';
  if(v==='strategic')return'strategic';
  if(v==='cartel'||v==='cartel/crime'||v==='crime')return'cartel';
  if(v==='osint')return'osint';
  return'all';
}
function layerSeverity(kind){
  if(kind==='conflicts'||kind==='cartel')return'critical';
  if(kind==='hazards')return'watch';
  if(kind==='osint'||kind==='strategic')return'info';
  return'info';
}
function opsTitle(p){
  return p.title||p.label||p.name||p.location||'Untitled signal';
}
function opsUpdatedAt(state){
  return state.mapPoints?.updatedAt||mapData?.points?.updatedAt||mapData?.events?.updatedAt||state.snapshot?.updatedAt||null;
}
function bindOpsHeaderFilters(){
  document.querySelectorAll('#section-map [data-layer]').forEach(btn=>{
    const norm=normalizeOpsFilter(btn.dataset.layer);
    btn.classList.toggle('active',norm===filter);
    if(btn.dataset.opsBound)return;btn.dataset.opsBound='1';
    btn.addEventListener('click',()=>{filter=normalizeOpsFilter(btn.dataset.layer);try{localStorage.setItem('gp.mapFilter',filter)}catch{}document.querySelectorAll('#section-map [data-layer]').forEach(b=>b.classList.toggle('active',normalizeOpsFilter(b.dataset.layer)===filter));renderMap();renderMapOps();});
  });
}
let opsSort='severity';
let opsShowAll=false;
let opsSev='all';
function signalSeverity(p){
  const c=String(p.confidence||p.verification||'').toLowerCase();
  if(/high|confirmed|corroborat|documented/.test(c))return'critical';
  if(/moderate|likely|reported|candidate|preliminary/.test(c))return'watch';
  if(c)return'info';
  const k=classify(p);
  if(k==='conflicts'||k==='cartel'||k==='hazards')return'watch';
  return'info';
}
function sigChip(sev){return sev==='critical'?'gp-sev-critical':sev==='watch'?'gp-sev-high':'gp-sev-medium'}
export function renderMapOps(){
  const host=document.getElementById('mapOpsBody');
  if(!host)return;
  bindOpsHeaderFilters();
  const state=getState()||{};
  if(!state.mapPoints&&!state.mapData&&!state.snapshot){
    host.innerHTML=state.status==='loading'
      ?'<div class="gp-state"><div class="gp-spinner"></div><div>Loading map operations…</div></div>'
      :'<div class="gp-state"><div class="gp-state-title">Map signals unavailable</div><div>Canonical map feed failed to load. Check source health below.</div></div>';
    return;
  }
  const all=collect();
  const counts=Object.fromEntries(OPS_LAYERS.map(k=>[k,0]));
  for(const p of all){try{counts[classify(p)]++}catch{}}
  const total=all.length;
  const visible=all.filter(matches);
  const shown0=visible;
  const sevOf=new Map();const sevCounts={all:visible.length,critical:0,watch:0,info:0};
  for(const p of shown0){const s=signalSeverity(p);sevOf.set(p,s);sevCounts[s]++}
  const sevFiltered=opsSev==='all'?visible:visible.filter(p=>sevOf.get(p)===opsSev);
  const rank={critical:0,watch:1,info:2};
  const sorted=[...sevFiltered].sort((a,b)=>{
    if(opsSort==='title')return String(opsTitle(a)).localeCompare(String(opsTitle(b)));
    if(opsSort==='layer')return classify(a).localeCompare(classify(b))||String(opsTitle(a)).localeCompare(String(opsTitle(b)));
    return (rank[sevOf.get(a)]-rank[sevOf.get(b)])||String(opsTitle(a)).localeCompare(String(opsTitle(b)));
  });
  const shown=opsShowAll?sorted:sorted.slice(0,OPS_MAX_ROWS);
  const engineNote=typeof L==='undefined'?'<div class="gp-honest" style="margin-bottom:8px">Map engine (Leaflet) did not load, so markers cannot be drawn. The operations list below still reflects the canonical feed.</div>':(typeof L.markerClusterGroup!=='function'?'<div class="gp-honest" style="margin-bottom:8px">Marker clustering plugin unavailable; signals render unclustered.</div>':'');
  const staleFeeds=Object.entries(state.feedMeta||{}).filter(([k,v])=>/^map|snapshot|intelligenceBrain/.test(k)&&v&&v.stale).map(([k])=>k);
  const staleNote=staleFeeds.length?`<div class="gp-honest" style="margin-bottom:8px">Some map feeds are stale (${escapeHtml(staleFeeds.join(', '))}); showing the last successful data.</div>`:'';
  const chips=['<button class="gp-filter'+(filter==='all'?' active':'')+'" data-map-ops-filter="all" type="button" aria-pressed="'+(filter==='all')+'">All ('+total.toLocaleString()+')</button>']
    .concat(OPS_LAYERS.map(k=>'<button class="gp-filter'+(filter===k?' active':'')+'" data-map-ops-filter="'+k+'" type="button" aria-pressed="'+(filter===k)+'">'+LAYERS[k].label+' ('+(counts[k]||0).toLocaleString()+')</button>')).join('');
  const sevChips=[['all','All severity'],['critical','Critical'],['watch','Watch'],['info','Informational']].map(([v,label])=>'<button class="gp-filter'+(opsSev===v?' active':'')+'" data-map-ops-sev="'+v+'" type="button" aria-pressed="'+(opsSev===v)+'">'+label+' ('+(sevCounts[v]||0).toLocaleString()+')</button>').join('');
  const rows=shown.map((p,i)=>{
    const k=classify(p);const m=LAYERS[k]||LAYERS.conflicts;const sev=sevOf.get(p);
    const title=opsTitle(p);const place=[p.country,p.region,p.city].filter(Boolean).join(' · ');
    const conf=p.confidence||p.verification||'';const src=p.source||'';
    const key=String(p.nodeId??p.id??p.eventId??(p.__lat+','+p.__lon)+':'+i);
    return '<button class="gp-map-op-row sev-'+sev+'" data-map-ops-focus="'+escapeHtml(key)+'" data-map-ops-index="'+i+'" type="button">'
      +'<span class="gp-map-op-dot" style="background:'+m.color+'"></span>'
      +'<span class="grow"><span class="title">'+escapeHtml(String(title).slice(0,140))+'</span>'
      +'<span class="meta">'+escapeHtml(m.label)+(place?' · '+escapeHtml(place):'')+(conf?' · '+escapeHtml(String(conf)):'')+(src?' · '+escapeHtml(String(src).slice(0,40)):'')+' · '+p.__lat.toFixed(2)+', '+p.__lon.toFixed(2)+'</span></span>'
      +'<span class="gp-sev '+sigChip(sev)+'">'+escapeHtml(conf?String(conf).slice(0,18):k)+'</span></button>';
  }).join('');
  host.innerHTML=engineNote+staleNote+'<div class="gp-map-ops-bar"><input id="mapOpsSearch" class="gp-map-search" type="search" aria-label="Filter map signals" placeholder="Filter map signals…" value="'+escapeHtml(query)+'">'
    +'<select id="mapOpsSort" class="gp-map-search" aria-label="Sort map signals" style="flex:0 0 150px"><option value="severity"'+(opsSort==='severity'?' selected':'')+'>Sort: severity</option><option value="title"'+(opsSort==='title'?' selected':'')+'>Sort: title</option><option value="layer"'+(opsSort==='layer'?' selected':'')+'>Sort: layer</option></select>'
    +'<span class="meta">Showing '+shown.length.toLocaleString()+' of '+sorted.length.toLocaleString()+' signals · '+total.toLocaleString()+' mapped points</span></div>'
    +'<div class="gp-filter-row" role="group" aria-label="Filter map by layer">'+chips+'</div>'
    +'<div class="gp-filter-row" role="group" aria-label="Filter map by confidence severity">'+sevChips+'</div>'
    +(rows?'<div class="gp-map-ops-list">'+rows+'</div>':'<div class="gp-state"><div class="gp-state-title">No signals match</div><div>Nothing in the canonical map feed matches this layer, severity or search.</div></div>')
    +(sorted.length>OPS_MAX_ROWS?'<button id="mapOpsMore" class="gp-btn gp-more" type="button">'+(opsShowAll?'Show fewer':'Show all '+sorted.length.toLocaleString())+'</button>':'');
  const search=host.querySelector('#mapOpsSearch');
  let opsTimer=0;
  search?.addEventListener('input',()=>{clearTimeout(opsTimer);const v=search.value.trim().toLowerCase();opsTimer=setTimeout(()=>{query=v;renderMap();renderMapOps();const again=document.getElementById('mapOpsSearch');if(again){again.focus();again.setSelectionRange(again.value.length,again.value.length)}},180)});
  host.querySelector('#mapOpsSort')?.addEventListener('change',e=>{opsSort=String(e.target.value||'severity');opsShowAll=false;renderMapOps()});
  host.querySelectorAll('[data-map-ops-filter]').forEach(btn=>btn.addEventListener('click',()=>{
    filter=normalizeOpsFilter(btn.dataset.mapOpsFilter);try{localStorage.setItem('gp.mapFilter',filter)}catch{}renderMap();renderMapOps();
  }));
  host.querySelectorAll('[data-map-ops-sev]').forEach(btn=>btn.addEventListener('click',()=>{opsSev=String(btn.dataset.mapOpsSev||'all');opsShowAll=false;renderMapOps()}));
  host.querySelector('#mapOpsMore')?.addEventListener('click',()=>{opsShowAll=!opsShowAll;renderMapOps()});
  host.querySelectorAll('[data-map-ops-index]').forEach(btn=>btn.addEventListener('click',()=>{
    const idx=Number(btn.dataset.mapOpsIndex);const p=shown[idx];if(!p)return;
    const kind=classify(p);
    if(!enabled[kind]){enabled[kind]=true;try{localStorage.setItem('gp.mapLayers',JSON.stringify(enabled))}catch{}renderMap()}
    if(map){map.setView([p.__lat,p.__lon],Math.max(map.getZoom(),5),{animate:false});showDetail(p);highlightMarker((groups[kind]&&groups[kind].getLayers?groups[kind].getLayers():[]).find(m=>m.__point===p)||null)}
    document.getElementById('mapContainer')?.scrollIntoView({behavior:'smooth',block:'center'});
  }));
  const stamp=document.getElementById('mapUpdated');
  if(stamp){const at=opsUpdatedAt(state);stamp.textContent=at?('Updated '+at.slice(0,16).replace('T',' ')+' UTC · '+total.toLocaleString()+' signals'):total.toLocaleString()+' signals'}
}
window.addEventListener('gp:brain-select',event=>{const id=event.detail?.id;if(!id||event.detail?.source==='map')return;const points=collect().filter(p=>String(p.nodeId??p.id??'')===String(id));if(!points.length)return;const p=points[0];const k=classify(p);if(!enabled[k]){enabled[k]=true;localStorage.setItem('gp.mapLayers',JSON.stringify(enabled));renderMap();return}if(map){map.setView([p.__lat,p.__lon],Math.max(map.getZoom(),5),{animate:false});showDetail(p)}});
if(['localhost','127.0.0.1'].includes(location.hostname)){window.addEventListener('gp:test-open-map-detail',()=>{const p=collect().find(matches);if(p)showDetail(p)})}
if(['localhost','127.0.0.1'].includes(location.hostname)){window.addEventListener('gp:test-map-debug',()=>{
  const el=document.getElementById('mapContainer');const r=el?.getBoundingClientRect();
  window.__gpMapDebug={checks:sizeChecks,fitted:!!renderMap._fitted,
    container:{w:Math.round(r?.width||0),h:Math.round(r?.height||0)},
    mapSize:map?{x:map.getSize().x,y:map.getSize().y}:null,
    zoom:map?map.getZoom():null,
    mapPane:(()=>{const p=document.querySelector('#mapContainer .leaflet-map-pane');const q=p?.getBoundingClientRect();return q?{w:Math.round(q.width)}:null})(),
    layers:Object.fromEntries(Object.entries(groups).map(([k,g])=>[k,g.getLayers().length]))};
})}
if(['localhost','127.0.0.1'].includes(location.hostname)){window.addEventListener('gp:test-click-marker-direct',()=>{
  const c=window.__gpTestClick;if(!c)return;
  const target=document.elementFromPoint(c.x,c.y)||document.getElementById('mapContainer');
  /* Non-bubbling: reaches canvas hit-testing but never the map container's
   * own click handler — isolates the marker path from map-click-close. */
  for(const t of ['mousedown','mouseup','click']){target.dispatchEvent(new MouseEvent(t,{bubbles:false,cancelable:true,clientX:c.x,clientY:c.y,button:0}))}
})}
if(['localhost','127.0.0.1'].includes(location.hostname)){window.addEventListener('gp:test-click-marker',()=>{
  const pts=collect().filter(matches);const el=document.getElementById('mapContainer');if(!map||!pts.length||!el)return;
  const p=pts[0];el.scrollIntoView({block:'center'});
  setTimeout(()=>{map.setView([p.__lat,p.__lon],Math.max(map.getZoom(),8),{animate:false});map.invalidateSize();
    setTimeout(()=>{const pt=map.latLngToContainerPoint([p.__lat,p.__lon]);const r=el.getBoundingClientRect();
      const cx=r.left+pt.x,cy=r.top+pt.y;const target=document.elementFromPoint(cx,cy)||el;
      window.__gpTestClick={x:Math.round(cx),y:Math.round(cy),title:opsTitle(p),target:target.tagName+'.'+(target.className?.baseVal??target.className??'')};
      for(const t of ['mousedown','mouseup','click']){target.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,clientX:cx,clientY:cy,button:0}))}},500);
  },400);
})}
