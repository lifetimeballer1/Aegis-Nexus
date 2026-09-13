/** Breaking / Latest Reporting — newest evidence first, five visible with See more. */
import { getState } from '../core/state.js';
import { formatRelativeTime, escapeHtml } from '../core/utils.js';
import { CONFIDENCE_LABELS } from '../core/config.js';
/* ---- story thumbnails (build-time manifest + category fallback art) ---- */
let thumbManifest = null;
function thumbSlug(t) { return String(t || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48); }
const THUMB_CATS = ['geopolitical', 'economic', 'indo-pacific', 'domestic', 'general', 'generic', 'regional', 'cartel', 'international', 'news', 'diplomatic', 'conflict', 'political'];
function thumbFallback(cat) {
  let c = String(cat || 'general').toLowerCase().replace(/[^a-z-]/g, '');
  if (THUMB_CATS.indexOf(c) >= 0) return c;
  if (/conflict|security/.test(c)) return 'conflict';
  if (/cartel/.test(c)) return 'cartel';
  if (/econom|market|trade/.test(c)) return 'economic';
  if (c === 'us-politics') return 'domestic';
  if (/politic|election/.test(c)) return 'political';
  if (/china|asia|pacific|indo/.test(c)) return 'indo-pacific';
  if (/geopolit|middle-east|europe|africa|americas|world/.test(c)) return 'geopolitical';
  if (/region|southcom/.test(c) || c === 'live') return 'regional';
  if (/diploma/.test(c)) return 'diplomatic';
  if (/intern/.test(c)) return 'international';
  return 'generic';
}
function thumbFor(title, cat) {
  const fb = 'assets/thumbs/fallback-' + thumbFallback(cat) + '.svg';
  const f = thumbManifest && thumbManifest[thumbSlug(title)];
  return { src: f ? ('assets/thumbs/' + f) : fb, fb };
}
function thumbImg(title, cat, cls) {
  const t = thumbFor(title, cat);
  return '<img class="' + cls + '" src="' + t.src + '" alt="" loading="lazy" onerror="this.onerror=null;this.src=\'' + t.fb + '\'">';
}
function loadThumbs(rerender) {
  fetch('assets/thumbs/manifest.json', { headers: { Accept: 'application/json' } })
    .then((r) => { if (!r.ok) throw new Error('no manifest'); return r.json(); })
    .then((m) => { thumbManifest = (m && m.map) || {}; if (rerender) { try { rerender(); } catch (e) {} } })
    .catch(() => {});
}

export function renderBreaking(){
 const el=document.getElementById('breakingBody'),updatedEl=document.getElementById('breakingUpdated');if(!el)return;const{liveArticles,snapshot}=getState();let items=Array.isArray(liveArticles)?liveArticles:liveArticles?.articles||snapshot?.stories||snapshot?.liveArticles||[];if(!items.length){el.innerHTML='<div class="gp-state"><div class="gp-state-title">No recent reports</div><div>Live article feed is empty or unavailable. Check source health below.</div></div>';return;}
 items=[...items].sort((a,b)=>new Date(b.published||b.publishedAt||b.published_date||b.publishedDate||b.time||b.date||0)-new Date(a.published||a.publishedAt||a.published_date||a.publishedDate||a.time||a.date||0));
 if(updatedEl&&items[0])updatedEl.textContent=formatRelativeTime(items[0].published||items[0].publishedAt||items[0].published_date||items[0].publishedDate||items[0].time);
 const render=(item,i)=>{const title=item.title||item.headline||'Untitled',summary=item.summary||item.summary_snippet||item.description||item.snippet||'',source=item.sourceLabel||item.sourceName||item.source||item.publisher||'Unknown source',url=item.url||item.link||item.sourceUrl||'#',time=item.published||item.publishedAt||item.published_date||item.publishedDate||item.time||item.date,raw=(item.confidence||item.conf||'limited').toString().toLowerCase(),key=raw.includes('high')||raw==='confirmed'?'high':raw.includes('mod')||raw==='likely'?'moderate':raw.includes('unver')?'unverified':raw.includes('conflict')?'conflicting':'limited',conf=CONFIDENCE_LABELS[key]||CONFIDENCE_LABELS.limited,category=item.tag||item.category||item.topic||(item.breaking?'BREAKING':'');return `<article class="gp-news-item ${i>=5?'gp-extra-item':''}" ${i>=5?'hidden':''}><div class="gp-news-main">${thumbImg(title, category, 'gp-news-thumb')}<div class="gp-news-body"><h3 class="gp-news-title"><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}</a></h3>${summary?`<p class="gp-news-summary">${escapeHtml(summary)}</p>`:''}<div class="gp-card-meta"><span class="gp-badge ${conf.class}">${conf.label}</span>${category?`<span class="gp-badge category">${escapeHtml(String(category))}</span>`:''}<span class="gp-source">${escapeHtml(source)}</span><span class="gp-time">${formatRelativeTime(time)}</span></div></div></div></article>`;};
 const capped=items.length>50;const shown=items.slice(0,50);el.innerHTML=`<div class="gp-news-list">${shown.map(render).join('')}</div>${capped?`<div class="meta" style="font-size:10px;color:var(--muted-2);margin:6px 0">Showing 50 of ${items.length} reports</div>`:''}${shown.length>5?`<button id="breakingMore" class="gp-btn gp-more" type="button">Show more reporting (${shown.length-5} more)</button>`:''}`;const more=document.getElementById('breakingMore');more?.addEventListener('click',()=>{const hidden=el.querySelectorAll('.gp-extra-item[hidden]');hidden.forEach(x=>x.hidden=false);more.remove();});
}
loadThumbs(() => { const b = typeof document !== 'undefined' && document.getElementById('breakingBody'); if (b && b.querySelector('.gp-news-item')) renderBreaking(); });
