// Seam geometry, focus roots, occluders, travel, bounds and the Trace map.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const T=vm.createContext({Math});vm.runInContext(fs.readFileSync(__dirname+'/../v4/Topology.js','utf8'),T);

function frame(windows,focus,extra){
  const f={focus:focus||windows[0].id,settings:{seeds:[322]},
    monitors:[{name:'DP-1',id:0,x:1080,y:0,width:1920,height:1080,workspace:1,focused:true,reserved:[0,35,0,0]}],
    workspaces:[{id:1,name:'1',monitor:0},{id:2,name:'2',monitor:0}],
    windows:windows.map(w=>Object.assign({monitor:0,workspace:1,app:'terminal',group:[],urgent:false,floating:false,fullscreen:false},w,{x:w.x+1080}))};
  if(extra)extra(f);return f;
}
// Hyprland-style dwindle: outer o, inner i (both include the 1px border).
function dwindle(o,i){
  const top=35,y=top+o,h=1080-top-2*o,left=Math.floor((1920-2*o-i)/2),half=Math.floor((h-i)/2);
  return [{id:'0x1',x:o,y,w:left,h},{id:'0x2',x:o+left+i,y,w:1920-2*o-i-left,h:half},{id:'0x3',x:o+left+i,y:y+half+i,w:1920-2*o-i-left,h:h-half-i}];
}
// Every coordinate pair in an SVG path string.
function points(d){const n=(d.match(/-?[0-9.]+/g)||[]).map(Number);const out=[];for(let i=0;i+1<n.length;i+=2)out.push({x:n[i],y:n[i+1]});return out;}
function grow(r,d){return {x:r.x-d,y:r.y-d,w:r.w+2*d,h:r.h+2*d};}
function noInk(g,tiledOnly){
  const rects=g.rects.filter(r=>!r.floating);
  // Core half-width matches Network.qml: 1px lines in tight (zero-gap) layouts, 1.5px otherwise.
  const reach=(g.minInset<2?0.5:0.75)+(g.focus&&g.focus.glow>0?g.focus.glow/2:0);
  for(const e of g.edges){const m={x:(e.a.x+e.b.x)/2,y:(e.a.y+e.b.y)/2};assert(!rects.some(r=>T.inside(m,r,0.5)),'seam inside a window');}
  if(g.focus)for(const p of g.focus.perimeter.points.filter((q,i,a)=>!g.focus.perimeter.open[q.side]))assert(!rects.some(r=>T.inside(p,grow(r,reach-0.01))),'focus root reaches a window: '+JSON.stringify(p));
  for(const d of [g.svg,g.focus?g.focus.full:''].concat(g.urgent.map(u=>u.svg)))assert(!/NaN|undefined/.test(d),'bad path');
}

// 1. Real 9/12 gaps: seams coincide on the gap centreline.
let g=T.graph(frame(dwindle(9,12),'0x1'),'DP-1','','',1920,1080);
assert.equal(g.frames.length,3);
assert.deepEqual(JSON.parse(JSON.stringify(g.frames[0].inset)),{open:{l:false,r:false,t:false,b:false},l:4.5,r:6,t:4.5,b:4.5});
assert.equal(g.frames[0].x1,g.frames[1].x0,'neighbour seams coincide');
assert(g.edges.some(e=>e.owners.length===2),'shared seam merged');
assert(g.junctions.length>=1,'T joint knot');
assert(g.focus&&g.focus.perimeter.wavy&&g.focus.glow>0);
noInk(g);

// 2. Zero gaps (1px borders only): straight seams on the border line, no glow.
g=T.graph(frame(dwindle(1,2),'0x2'),'DP-1','0x1','0x2',1920,1080);
assert.equal(g.frames.length,3);assert(g.minInset<2);
assert(!g.focus.perimeter.wavy&&g.focus.glow<0);
noInk(g);
// No gap AND no border: there is no space at all. Seams still sit exactly on
// the shared edge (a documented limit: the line overlaps the outermost pixel).
g=T.graph(frame([{id:'0x1',x:0,y:35,w:960,h:1045},{id:'0x2',x:960,y:35,w:960,h:1045}]),'DP-1','','',1920,1080);
assert.equal(g.frames[0].x1,960);assert.equal(g.frames[1].x0,960);assert.equal(g.minInset,0);

// 3. One window per workspace: its own frame in the outer margin.
g=T.graph(frame([{id:'0x1',x:9,y:44,w:1902,h:1027}]),'DP-1','','',1920,1080);
assert.equal(g.frames.length,1);assert.equal(g.edges.length,4);noInk(g);

// 4. Floating windows add no seams and nothing is drawn across them.
const float={id:'0x9',x:700,y:320,w:520,h:380,floating:true};
g=T.graph(frame(dwindle(9,12).concat([float]),'0x1',f=>{f.windows[1].urgent=true}),'DP-1','','',1920,1080);
assert.equal(g.frames.length,3);assert.equal(g.occluders.length,1);
const occ=g.occluders[0];
for(const d of [g.svg,g.focus.full].concat(g.urgent.map(u=>u.svg)))for(const p of points(d))assert(!T.inside(p,occ),'ink across floating window '+JSON.stringify(p));
for(const t of [0.1,0.37,0.5,0.81])for(const p of points(T.grown(g.focus.perimeter,g.focus.start,t,g.occluders)))assert(!T.inside(p,occ));
noInk(g);

// 5. Focus growth starts on the side facing the previous window.
g=T.graph(frame(dwindle(9,12),'0x2'),'DP-1','0x1','0x2',1920,1080);
const start=T.at(g.focus.perimeter,g.focus.start);
// On the shared seam (within the root's wave amplitude), at its middle.
assert(Math.abs(start.x-g.frames[1].x0)<=2.5&&Math.abs(start.y-(g.frames[1].y0+g.frames[1].y1)/2)<3,'growth starts mid shared seam '+JSON.stringify(start));
assert.equal(g.travel.length,0,'adjacent windows need no spark');
assert.equal(T.grown(g.focus.perimeter,g.focus.start,0,[]),'');

// 6. Non-adjacent windows: a spark path along the seams.
const cols=[0,1,2].map(k=>({id:'0x'+(k+1),x:9+k*638,y:44,w:626,h:1027}));
g=T.graph(frame(cols,'0x3'),'DP-1','0x1','0x3',1920,1080);
assert(g.travel.length>=2,'spark path');
for(const p of g.travel)assert(g.frames.some(f=>(p.x===f.x0||p.x===f.x1)&&p.y>=f.y0&&p.y<=f.y1||(p.y===f.y0||p.y===f.y1)&&p.x>=f.x0&&p.x<=f.x1),'spark leaves the seams');
noInk(g);

// 7. Unplugged output, tiny surface and fullscreen.
assert(T.graph(frame(cols),'UNPLUGGED','','',1920,1080).off);
assert.equal(T.graph(frame(cols),'DP-1','','',60,60).frames.length,0);
assert(T.graph(frame(cols,'0x1',f=>{f.windows[0].fullscreen=true}),'DP-1','','',1920,1080).fullscreen);

// 8. Bounds under stress.
const crowd=Array.from({length:80},(_,i)=>({id:'0x'+(i+16).toString(16),x:(i%10)*190+4,y:40+Math.floor(i/10)*130,w:180,h:120}));
let t0=Date.now();
for(let i=0;i<20;i++){const s=T.graph(frame(crowd,'0x10'),'DP-1','0x11','0x10',1920,1080);assert(s.frames.length<=24);assert(s.junctions.length<=32);assert.equal(s.omitted,56);}
const stress=(Date.now()-t0)/20;

// 9. Review regressions: nothing may be drawn over a window in odd layouts.
function inkPoints(g){return [g.svg,g.focus?g.focus.full:''].concat(g.urgent.map(u=>u.svg)).flatMap(points);}
function clean(g,label){const rects=g.rects.filter(r=>!r.floating);for(const p of inkPoints(g))assert(!rects.some(r=>T.inside(p,r,0.25)),label+': ink inside a window '+JSON.stringify(p));noInk(g);}
// Scrolling layout: windows hang off both screen edges; one is fully off-screen.
g=T.graph(frame([{id:'0xa',x:-50,y:44,w:300,h:1027},{id:'0xb',x:262,y:44,w:1247,h:1027},{id:'0xc',x:1521,y:44,w:1000,h:1027},{id:'0xd',x:2600,y:44,w:900,h:1027}],'0xa'),'DP-1','','',1920,1080);
assert.equal(g.frames.length,3,'off-screen window skipped');assert(g.frames[0].open.l&&g.frames[2].open.r,'off-screen sides open');clean(g,'scrolling');
// A lone centred window with large margins still gets room around it.
g=T.graph(frame([{id:'0x1',x:100,y:100,w:1720,h:880}]),'DP-1','','',1920,1080);
assert.equal(g.frames[0].inset.l,12);clean(g,'centred');
// Flush to the screen edge with no border: that side stays open.
g=T.graph(frame([{id:'0x1',x:0,y:44,w:1911,h:1027}]),'DP-1','','',1920,1080);
assert(g.frames[0].open.l&&!g.frames[0].open.r);clean(g,'flush');
// Overlapping tiled windows (mid-resize): the overlapped side has no seam.
g=T.graph(frame([{id:'0x1',x:9,y:44,w:960,h:1027},{id:'0x2',x:950,y:44,w:961,h:1027}],'0x2'),'DP-1','0x1','0x2',1920,1080);
assert(g.frames[1].open.l&&g.frames[0].open.r);
// Floating glow and the 24-window bound: a wide cut, and overflow windows occlude.
g=T.graph(frame(dwindle(21,22).concat([{id:'0x9',x:900,y:300,w:200,h:200,floating:true}]),'0x1'),'DP-1','','',1920,1080);
assert(g.focus.glow>4&&g.focus.pad>=1.75+g.focus.glow/2);
for(const p of points(g.focus.full))assert(!T.inside(p,{x:900-g.focus.pad+0.1,y:300-g.focus.pad+0.1,w:200+2*g.focus.pad-0.2,h:200+2*g.focus.pad-0.2}),'glow reaches floating window'); // SVG keeps 0.1px precision
const over=T.graph(frame(crowd,'0x10'),'DP-1','','',1920,1080);assert.equal(over.occluders.length,56,'overflow windows occlude');
// An open scratchpad (special workspace) covers the tiled layer.
g=T.graph(frame(dwindle(9,12),'0x1',f=>{f.monitors[0].special=-98;f.windows.push({id:'0x99',x:1080+400,y:200,w:1100,h:700,monitor:0,workspace:-98,app:'s',floating:true})}),'DP-1','','',1920,1080);
assert.equal(g.occluders.length,1);for(const p of points(g.svg))assert(!T.inside(p,g.occluders[0]),'seam across the scratchpad');

// 10. Trace map: every workspace, hop roots along gutter seams, pages.
const many=frame(dwindle(9,12),'0x1',f=>{
  f.workspaces=[1,2,3,4].map(i=>({id:i,name:String(i),monitor:0}));
  f.windows.push(Object.assign({},f.windows[0],{id:'0x21',workspace:2}),Object.assign({},f.windows[0],{id:'0x31',workspace:3,urgent:true}));
});
const area={x:32,y:230,w:1856,h:760};
let fo=T.forest(many,[{a:1,b:2},{a:2,b:4},{a:1,b:4},{a:2,b:1}],area,0,170);
assert.equal(fo.tiles.length,4);assert.equal(fo.pages,1);
assert.equal(fo.tiles[0].windows.length,3);assert(fo.tiles[2].urgent);assert(fo.tiles[0].current&&fo.tiles[0].focused);
assert.equal(fo.roots.length,3,'1:2, 2:4 and diagonal 1:4');
assert(fo.roots.every(r=>r.svg&&!/NaN|undefined/.test(r.svg)));
assert(fo.roots.find(r=>r.id==='1:2').count===2&&fo.roots.find(r=>r.id==='1:2').last);
for(const t of fo.tiles){assert(t.x>=area.x-0.5&&t.x+t.w<=area.x+area.w+0.5&&t.y-20>=area.y-0.5&&t.y+t.h<=area.y+area.h+0.5,'tile outside area');
  for(const w of t.windows)assert(w.x>=0&&w.y>=0&&w.x+w.w<=t.w+0.01&&w.y+w.h<=t.h+0.01,'mini window outside tile');}
for(let i=0;i<fo.tiles.length;i++)for(let j=0;j<i;j++){const a=fo.tiles[i],b=fo.tiles[j];assert(a.x+a.w<=b.x||b.x+b.w<=a.x||a.y+a.h<=b.y-20||b.y+b.h<=a.y-20,'tiles overlap');}
// Roots never cross a tile.
for(const r of fo.roots)for(const p of points(r.svg))assert(!fo.tiles.some(t=>T.inside(p,{x:t.x,y:t.y-20,w:t.w,h:t.h+20})),'root crosses a tile');
// 24 workspaces on a small output page instead of shrinking past legibility.
many.workspaces=Array.from({length:24},(_,i)=>({id:i+1,name:String(i+1),monitor:0}));
fo=T.forest(many,[],{x:12,y:80,w:296,h:200},0,110);
assert(fo.pages>1&&fo.perPage>=1);assert(fo.tiles.every(t=>t.w>=110));
assert.equal(T.forest(many,[],{x:12,y:80,w:296,h:200},99,110).page,fo.pages-1,'page clamps');
console.log('PASS seams at 0/9/12 gaps, single window, floating occluder, growth origin, spark path, bounds, Trace map + pages; stress mean ms',stress.toFixed(2));
