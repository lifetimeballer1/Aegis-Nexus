const {test}=require('node:test');
const assert=require('node:assert/strict');
const {project}=require('../js/intelligence_web_filters.js');
const now=Date.parse('2026-09-08T12:00:00Z');
const recent={time:'2026-09-08T10:00:00Z',title:'Recent source'};
const old={time:'2026-09-01T10:00:00Z',title:'Older source'};
const node=(id,kind,evidence=[recent])=>({id,label:id,kind,evidence});
const edge=(source,target,evidence=[recent])=>({source,target,evidence});

test('UI categories resolve canonical kinds, not headline keywords',()=>{
  const base={nodes:[node('Bank','financial_institution'),node('Firm','company'),node('Fund story','person')],links:[]};
  assert.deepEqual(project(base,{category:'economic'}).focus.map(n=>n.id),['Bank','Firm']);
  assert.equal(project(base,{category:'military'}).nodes.length,0);
});
test('time range uses source dates, excluding old, undated and future evidence',()=>{
  const base={nodes:[node('A','country',[recent,old,{}, {time:'2027-01-01T00:00:00Z'}]),node('B','country',[old])],links:[]};
  const result=project(base,{period:'24',now});
  assert.deepEqual(result.nodes.map(n=>n.id),['A']);
  assert.deepEqual(result.nodes[0].evidence,[recent]);
  assert.equal(base.nodes[0].evidence.length,4);
  assert.equal(project(base,{period:'all',now}).nodes.length,2);
});
test('window boundaries are inclusive and refresh timestamps do not make stale sources current',()=>{
  const base={nodes:[node('Boundary','country',[{time:'2026-09-07T12:00:00Z'}]),{...node('Stale','country',[old]),updatedAt:new Date(now).toISOString()}],links:[]};
  assert.deepEqual(project(base,{period:'24',now}).nodes.map(n=>n.id),['Boundary']);
});
test('search is case-insensitive and preserves only direct connections',()=>{
  const base={nodes:[node('China','country'),node('Japan','country'),node('Canada','country')],links:[edge('China','Japan'),edge('China','Canada'),edge('Japan','Canada')]};
  const result=project(base,{query:'  CHINA  '});
  assert.equal(result.focus.length,1);
  assert.equal(result.nodes.length,3);
  assert.equal(result.links.length,2);
  assert.equal(project(base,{query:'no such entity'}).nodes.length,0);
});
test('time and category filters compose while keeping recent edge endpoints',()=>{
  const base={nodes:[node('China','country',[old]),node('Bank','financial_institution',[old])],links:[edge('China','Bank')]};
  const result=project(base,{query:'bank',category:'economic',period:'24',now});
  assert.deepEqual(result.focus.map(n=>n.id),['Bank']);
  assert.equal(result.nodes.length,2);
  assert.equal(result.links.length,1);
});
test('expired edges do not reappear through recently mentioned nodes',()=>{
  const base={nodes:[node('A','country'),node('B','country')],links:[edge('A','B',[old])]};
  assert.equal(project(base,{period:'24',now}).links.length,0);
});
test('renderer-mutated endpoints and dangling edges are handled without mutating the source graph',()=>{
  const base={nodes:[node('A','country'),node('B','country')],links:[edge({id:'A'},{id:'B'}),edge('A','missing')]};
  const result=project(base);
  assert.equal(result.links.length,1);
  assert.equal(result.links[0].source,'A');
  assert.deepEqual(base.links[0].source,{id:'A'});
  result.nodes[0].x=99;
  assert.equal(base.nodes[0].x,undefined);
});
