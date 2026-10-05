const fs=require('fs'),vm=require('vm'),assert=require('assert');
const T=vm.createContext({Math});vm.runInContext(fs.readFileSync(__dirname+'/../v3/Topology.js','utf8'),T);
const rects=[{x:90,y:100,w:340,h:450},{x:460,y:100,w:390,h:450}];
const p=T.route({x:8,y:280},{x:451,y:340},rects,1000,700);
assert(p.length>=3);for(let i=1;i<p.length;i++)assert(T.clear(p[i-1],p[i],rects));
const frame={focus:'0x2',settings:{seeds:[322]},monitors:[{name:'DP-1',id:0,x:0,y:0,workspace:1}],workspaces:[{id:1,name:'1'},{id:2,name:'2'}],windows:[
{id:'0x1',monitor:0,workspace:1,x:90,y:100,w:340,h:450,app:'terminal',group:['0x2'],urgent:true},
{id:'0x2',monitor:0,workspace:1,x:460,y:100,w:390,h:450,app:'browser',group:[]} ]};
const g=T.graph(frame,'DP-1',[{a:'0x1',b:'0x2',kind:'focus'}],null,1000,700);
assert.equal(g.nodes.length,2);assert(g.paths.some(p=>p.kind==='group'));assert(g.paths.some(p=>p.kind==='focus'));assert(g.nodes.some(n=>n.urgent));
for(const path of g.paths)for(let i=1;i<path.points.length;i++)assert(T.clear(path.points[i-1],path.points[i],g.rects));
assert(T.graph(frame,'UNPLUGGED',[],null,1000,700).off);
const moved=JSON.parse(JSON.stringify(frame));moved.windows[0].workspace=2;
assert(T.graph(moved,'DP-1',[],frame,1000,700).paths.some(p=>p.kind==='move'));
const crowded=JSON.parse(JSON.stringify(frame));crowded.windows=Array.from({length:80},(_,i)=>({...frame.windows[i%2],id:'0x'+(i+10).toString(16)}));
let start=performance.now();for(let i=0;i<50;i++){let x=T.graph(crowded,'DP-1',[],null,1000,700);assert(x.nodes.length<=24);assert(x.paths.length<=64)}
console.log('PASS geometry, truthful links, grouping, portals, unplug, bounds; stress mean ms',((performance.now()-start)/50).toFixed(2));
