const fs=require('fs'),vm=require('vm'),assert=require('assert');
const T=vm.createContext({Math});vm.runInContext(fs.readFileSync(__dirname+'/../v3/Topology.js','utf8'),T);
function fixture(W,H,gap=9,split=false){
 const m={name:'fixture',id:0,x:1080,y:0,workspace:1};
 const windows=[{id:'0x1',x:1080+gap,y:44,w:W-2*gap,h:H-53,monitor:0,workspace:1,app:'terminal',group:[]}];
 if(split){windows[0].w=(W-2*gap-12)/2;windows.push({...windows[0],id:'0x2',app:'browser',x:1080+gap+windows[0].w+12})}
 return {monitors:[m],windows,focus:windows[0].id,workspaces:[{id:1},{id:2}],settings:{seeds:[78351]}};
}
for(const [W,H] of [[1920,1080],[1280,720],[960,540],[2560,1440]])for(const split of [false,true]){
 const f=fixture(W,H,9,split),g=T.graph(f,'fixture',split?[{a:'0x1',b:'0x2',kind:'focus'}]:[],null,W,H);
 assert.equal(g.nodes.length,split?2:1,`tiled ${W}x${H}`);
 assert.equal(g.paths.filter(p=>p.kind==='root').length,g.nodes.length);
 for(const n of g.nodes){assert(n.clearance>=4);assert(!g.rects.some(r=>T.inside(n,r)))}
 for(const p of g.paths)for(let i=1;i<p.points.length;i++)assert(T.clear(p.points[i-1],p.points[i],g.rects));
 if(split)assert(g.paths.some(p=>p.kind==='focus'));
}
const none=fixture(1920,1080,0);none.windows[0].y=0;none.windows[0].h=1080;
assert.equal(T.graph(none,'fixture',[],null,1920,1080).nodes.length,0);
none.windows[0].fullscreen=true;assert(T.graph(none,'fixture',[],null,1920,1080).fullscreen);
// Execute the actual service status function, including fullscreen and zero space.
const svc=fs.readFileSync(__dirname+'/../v3/Service.qml','utf8');
const status=svc.slice(svc.indexOf('function outputStatus('),svc.indexOf('function ingest('));
const ctx=vm.createContext({frame:none,paused:false,unavailable:false,reducedMotion:false,settled:true});vm.runInContext(status,ctx);
assert.equal(ctx.outputStatus('fixture',0),'Ambient hidden by fullscreen');none.windows[0].fullscreen=false;
assert.equal(ctx.outputStatus('fixture',0),'No room for roots on this workspace');ctx.paused=true;assert.equal(ctx.outputStatus('fixture',1),'Ambient paused');ctx.paused=false;ctx.reducedMotion=true;assert.equal(ctx.outputStatus('fixture',1),'Still roots · motion off');
console.log('PASS 9px outer / 12px tiled gaps at 960–2560 logical widths, paths avoid app interiors; fullscreen/no-space/still/paused statuses');
