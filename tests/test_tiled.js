// Real tiling layouts at common resolutions and gap sizes, plus the actual
// service status strings executed from Service.qml.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const T=vm.createContext({Math});vm.runInContext(fs.readFileSync(__dirname+'/../v4/Topology.js','utf8'),T);
function layout(W,H,o,i,count){
  const top=35,y=top+o,h=H-top-2*o,ws=[];
  if(count===1)return [{id:'0x1',x:o,y,w:W-2*o,h}];
  const left=Math.floor((W-2*o-i)/2);ws.push({id:'0x1',x:o,y,w:left,h});
  const rest=count-1,each=Math.floor((h-(rest-1)*i)/rest);
  for(let k=0;k<rest;k++)ws.push({id:'0x'+(k+2),x:o+left+i,y:y+k*(each+i),w:W-2*o-i-left,h:k===rest-1?h-k*(each+i):each});
  return ws;
}
function frame(W,H,windows,focus){
  return {focus,settings:{seeds:[78351]},monitors:[{name:'fixture',id:0,x:1080,y:0,width:W,height:H,workspace:1,reserved:[0,35,0,0]}],
    workspaces:[{id:1},{id:2}],windows:windows.map(w=>Object.assign({monitor:0,workspace:1,app:'a',urgent:false,floating:false,fullscreen:false},w,{x:w.x+1080}))};
}
let checked=0;
for(const [W,H] of [[960,540],[1280,720],[1920,1080],[2560,1440]])
for(const [o,i] of [[0,0],[1,2],[9,12],[21,22]])
for(const count of [1,2,3,5]){
  const wins=layout(W,H,o,i,count),g=T.graph(frame(W,H,wins,'0x1'),'fixture','','',W,H);
  assert.equal(g.frames.length,count,`${W}x${H} gaps ${o}/${i} x${count}`);
  // One borderless window filling the screen has no seam at all: nothing to draw.
  if(o>0||count>1)assert(g.svg.length>0&&g.focus,'seams drawn');else assert.equal(g.svg,'');
  if(count>1&&i<64)assert(g.edges.some(e=>e.owners.length>1),'neighbours share a seam');
  const rects=g.rects,hasRoom=Math.min(o,i/2)>0;
  if(hasRoom){
    const reach=(g.minInset<2?0.5:0.75)+(g.focus.glow>0?g.focus.glow/2:0);
    for(const e of g.edges){const m={x:(e.a.x+e.b.x)/2,y:(e.a.y+e.b.y)/2};assert(!rects.some(r=>T.inside(m,r,0.5)),'seam inside window')}
    for(const p of g.focus.perimeter.points)assert(!rects.some(r=>T.inside(p,{x:r.x-reach+0.01,y:r.y-reach+0.01,w:r.w+2*reach-0.02,h:r.h+2*reach-0.02})),`root reaches a window at ${W}x${H} ${o}/${i}`);
  }
  checked++;
}
// Execute the actual service status function.
const svc=fs.readFileSync(__dirname+'/../v4/Service.qml','utf8');
const status=svc.slice(svc.indexOf('function outputStatus('),svc.indexOf('function geometryKey('));
const one=frame(1920,1080,layout(1920,1080,9,12,1),'0x1');
const ctx=vm.createContext({frame:one,paused:false,unavailable:false,reducedMotion:false,settled:true,response:'Focus moved'});vm.runInContext(status,ctx);
assert.equal(ctx.outputStatus('fixture',1),'Roots resting on your window seams');
one.windows[0].fullscreen=true;assert.equal(ctx.outputStatus('fixture',1),'Ambient hidden by fullscreen');one.windows[0].fullscreen=false;
assert.equal(ctx.outputStatus('fixture',0),'No tiled windows on this workspace');
ctx.settled=false;assert.equal(ctx.outputStatus('fixture',1),'Roots responding · focus moved');ctx.settled=true;
ctx.paused=true;assert.equal(ctx.outputStatus('fixture',1),'Ambient paused');ctx.paused=false;
ctx.reducedMotion=true;assert.equal(ctx.outputStatus('fixture',1),'Still roots · motion off');ctx.reducedMotion=false;
ctx.unavailable=true;assert.equal(ctx.outputStatus('fixture',1),'Waiting for desktop connection');
console.log(`PASS ${checked} tiled layouts (960–2560 wide, gaps 0/0 1/2 9/12 21/22, 1–5 windows): seams drawn, neighbours share seams, roots stay out of windows; real statuses`);
