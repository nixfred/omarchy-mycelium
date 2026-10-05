// Pure bounded geometry. Routing uses a rectilinear visibility grid in gaps.
// Structural roots are not data transfers. Relationships are observed focus/group.
var LIMITS = {windows: 24, links: 32, cells: 4096, visits: 4096, tendrils: 96};
function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
function hash(s) { var h=2166136261; for(var i=0;i<s.length;i++) h=Math.imul(h^s.charCodeAt(i),16777619); return h>>>0; }
function inside(p, r) { return p.x>r.x-4 && p.x<r.x+r.w+4 && p.y>r.y-4 && p.y<r.y+r.h+4; }
function clear(a,b,rects) {
  for(var i=0;i<rects.length;i++) {
    var r=rects[i];
    if(a.x===b.x && a.x>r.x-4 && a.x<r.x+r.w+4 && Math.max(a.y,b.y)>r.y-4 && Math.min(a.y,b.y)<r.y+r.h+4) return false;
    if(a.y===b.y && a.y>r.y-4 && a.y<r.y+r.h+4 && Math.max(a.x,b.x)>r.x-4 && Math.min(a.x,b.x)<r.x+r.w+4) return false;
  } return true;
}
// Distance to occupied rectangles and the usable output edge. All visual knots
// fit inside this radius, including the actual 9px outer / 12px tiled gaps.
function clearance(p,rects,W,H) {
  var distance=Math.min(p.x,W-p.x,p.y-48,H-p.y);
  rects.forEach(function(r){
    var dx=Math.max(r.x-p.x,0,p.x-r.x-r.w),dy=Math.max(r.y-p.y,0,p.y-r.y-r.h);
    distance=Math.min(distance,Math.hypot(dx,dy));
  });return Math.max(0,distance);
}
function unique(a) { return a.sort(function(x,y){return x-y;}).filter(function(v,i,s){return !i || v!==s[i-1];}); }
function route(a,b,rects,W,H) {
  var xs=[4,W-4,a.x,b.x],ys=[52,H-4,a.y,b.y];
  rects.forEach(function(r){ xs.push(clamp(r.x-5,4,W-4),clamp(r.x+r.w+5,4,W-4)); ys.push(clamp(r.y-5,52,H-4),clamp(r.y+r.h+5,52,H-4)); });
  xs=unique(xs);ys=unique(ys);
  if(xs.length*ys.length>LIMITS.cells) return [];
  var start=ys.indexOf(a.y)*xs.length+xs.indexOf(a.x), end=ys.indexOf(b.y)*xs.length+xs.indexOf(b.x);
  var dist={},prev={},queue=[[0,start]],visits=0;
  dist[start]=0;
  function point(n){return {x:xs[n%xs.length],y:ys[Math.floor(n/xs.length)]};}
  function push(v){queue.push(v);var i=queue.length-1;while(i){var j=(i-1)>>1;if(queue[j][0]<=v[0])break;queue[i]=queue[j];i=j;}queue[i]=v;}
  function pop(){var v=queue[0],tail=queue.pop();if(queue.length){var i=0;while(i*2+1<queue.length){var j=i*2+1;if(j+1<queue.length&&queue[j+1][0]<queue[j][0])j++;if(queue[j][0]>=tail[0])break;queue[i]=queue[j];i=j;}queue[i]=tail;}return v;}
  while(queue.length && visits++<LIMITS.visits) {
    var pair=pop(),d=pair[0],n=pair[1];if(dist[n]!==d)continue;if(n===end)break;
    var x=n%xs.length,y=Math.floor(n/xs.length),p=point(n),near=[];
    if(x)near.push(n-1);if(x<xs.length-1)near.push(n+1);if(y)near.push(n-xs.length);if(y<ys.length-1)near.push(n+xs.length);
    near.forEach(function(k){var q=point(k);if(!clear(p,q,rects))return;var nd=d+Math.abs(q.x-p.x)+Math.abs(q.y-p.y);if(dist[k]===undefined||nd<dist[k]){dist[k]=nd;prev[k]=n;push([nd,k]);}});
  }
  if(dist[end]===undefined)return [];
  var path=[],cur=end;while(cur!==undefined){path.unshift(point(cur));if(cur===start)break;cur=prev[cur];}
  return path.filter(function(p,i,s){return !i||i===s.length-1||!((s[i-1].x===p.x&&p.x===s[i+1].x)||(s[i-1].y===p.y&&p.y===s[i+1].y));});
}
function svg(points) {
  if(!points.length)return "";
  var out="M "+points[0].x+" "+points[0].y;
  for(var i=1;i<points.length;i++) {
    var p=points[i],last=points[i-1],next=points[i+1];
    if(!next){out+=" L "+p.x+" "+p.y;continue;}
    var radius=Math.min(5,Math.hypot(p.x-last.x,p.y-last.y)/3,Math.hypot(next.x-p.x,next.y-p.y)/3);
    var before={x:p.x+Math.sign(last.x-p.x)*radius,y:p.y+Math.sign(last.y-p.y)*radius};
    var after={x:p.x+Math.sign(next.x-p.x)*radius,y:p.y+Math.sign(next.y-p.y)*radius};
    out+=" L "+before.x+" "+before.y+" Q "+p.x+" "+p.y+" "+after.x+" "+after.y;
  } return out;
}
function organic(points,rects,seed,W,H) {
  if(!points.length)return "";
  var out="M "+points[0].x+" "+points[0].y;
  for(var i=1;i<points.length;i++) {
    var a=points[i-1],b=points[i],horizontal=a.y===b.y,len=Math.hypot(b.x-a.x,b.y-a.y),chunks=Math.max(1,Math.ceil(len/160));
    for(var j=0;j<chunks;j++) {
      var s={x:a.x+(b.x-a.x)*j/chunks,y:a.y+(b.y-a.y)*j/chunks},e={x:a.x+(b.x-a.x)*(j+1)/chunks,y:a.y+(b.y-a.y)*(j+1)/chunks};
      var amp=Math.min(12,len/chunks/7)*(hash(String(seed)+i+j)%2?1:-1);
      function fits(v) {
        var box={x:Math.min(s.x,e.x)-(horizontal?0:Math.abs(v)),y:Math.min(s.y,e.y)-(horizontal?Math.abs(v):0),w:Math.abs(e.x-s.x)+(horizontal?0:Math.abs(v)*2),h:Math.abs(e.y-s.y)+(horizontal?Math.abs(v)*2:0)};
        return box.x>=0 && box.x+box.w<=W && box.y>=52 && box.y+box.h<=H && !rects.some(function(r){return box.x+box.w>r.x-3&&box.x<r.x+r.w+3&&box.y+box.h>r.y-3&&box.y<r.y+r.h+3;});
      }
      for(var k=0;k<5&&!fits(amp);k++)amp/=2;
      if(!fits(amp))amp=0;
      var c1={x:s.x+(e.x-s.x)*0.33+(horizontal?0:amp),y:s.y+(e.y-s.y)*0.33+(horizontal?amp:0)};
      var c2={x:s.x+(e.x-s.x)*0.66+(horizontal?0:-amp*0.35),y:s.y+(e.y-s.y)*0.66+(horizontal?-amp*0.35:0)};
      out+=" C "+c1.x+" "+c1.y+" "+c2.x+" "+c2.y+" "+e.x+" "+e.y;
    }
  }return out;
}
function sample(points,t) {
  var lengths=[],total=0;
  for(var i=1;i<points.length;i++){var l=Math.hypot(points[i].x-points[i-1].x,points[i].y-points[i-1].y);lengths.push(l);total+=l;}
  var target=clamp(t,0,1)*total;
  for(var j=0;j<lengths.length;j++){if(target<=lengths[j]){var f=lengths[j]?target/lengths[j]:0;return {x:points[j].x+(points[j+1].x-points[j].x)*f,y:points[j].y+(points[j+1].y-points[j].y)*f};}target-=lengths[j];}
  return points.length?points[points.length-1]:{x:0,y:0};
}
function partial(points,t) {
  if(t>=0.999)return svg(points);
  if(!points.length)return "";
  var out=[points[0]],total=0;
  for(var i=1;i<points.length;i++)total+=Math.hypot(points[i].x-points[i-1].x,points[i].y-points[i-1].y);
  var budget=total*clamp(t,0,1);
  for(var j=1;j<points.length;j++){
    var len=Math.hypot(points[j].x-points[j-1].x,points[j].y-points[j-1].y);if(!len)continue;
    if(budget<len){out.push({x:points[j-1].x+(points[j].x-points[j-1].x)*budget/len,y:points[j-1].y+(points[j].y-points[j-1].y)*budget/len});break;}
    out.push(points[j]);budget-=len;
  }return svg(out);
}
function graph(frame,name,edges,previous,W,H) {
  var m=(frame.monitors||[]).filter(function(m){return m.name===name;})[0];
  if(!m)return {nodes:[],paths:[],portals:[],off:true};
  if(W<80||H<80)return {nodes:[],paths:[],portals:[],off:m.off};
  var all=(frame.windows||[]).filter(function(w){return w.monitor===m.id && w.workspace===m.workspace;});
  var rects=all.map(function(w){return {x:w.x-m.x,y:w.y-m.y,w:w.w,h:w.h};});
  var nodes=[],paths=[],portals=[],lookup={};
  var seeds=frame.settings&&frame.settings.seeds||[73217],seed=seeds[Math.abs(m.workspace)%seeds.length];
  // Workspace-specific root location, always on the free outer corridor.
  var hub={x:4,y:clamp(100+(seed%Math.max(1,Math.floor(H-200))),52,H-4)};
  hub.clearance=clearance(hub,rects,W,H);
  var ideal={x:W*(0.28+(seed%100)/250),y:H*(0.35+((seed>>>8)%100)/500)},best=-1e9;
  // Find a generous existing gap for the root ganglion. Never a window interior.
  var gapX=unique([4,24,W/2,W-24,W-4].concat(rects.map(function(r){return clamp(r.x+r.w+5,4,W-4);})).concat(rects.map(function(r){return clamp(r.x-5,4,W-4);}))),gapY=unique([52,150,H/2,H-100,H-4].concat(rects.map(function(r){return clamp(r.y+r.h+5,52,H-4);})));
  gapX.slice(0,32).forEach(function(x){gapY.slice(0,32).forEach(function(y){
    var p={x:x,y:y};if(rects.some(function(r){return inside(p,r);}))return;
    var room=clearance(p,rects,W,H);
    var score=room*2-Math.hypot(x-ideal.x,y-ideal.y)*0.12;
    if(room>=4&&score>best){best=score;p.clearance=room;hub=p;}
  });});
  var candidates=all.slice().sort(function(a,b){return (b.id===frame.focus?4:b.urgent?2:0)-(a.id===frame.focus?4:a.urgent?2:0);});
  candidates.slice(0,LIMITS.windows).forEach(function(w,i){
    var r={x:w.x-m.x,y:w.y-m.y,w:w.w,h:w.h},options=[{x:r.x-5,y:clamp(r.y+r.h/2,52,H-4)}, {x:r.x+r.w+5,y:clamp(r.y+r.h/2,52,H-4)}, {x:clamp(r.x+r.w/2,4,W-4),y:r.y-5}, {x:clamp(r.x+r.w/2,4,W-4),y:r.y+r.h+5}];
    var p=options.filter(function(p){return p.x>=4&&p.x<=W-4&&p.y>=52&&p.y<=H-4&&!rects.some(function(q){return inside(p,q);});})[0];
    if(!p)return;
    p.clearance=clearance(p,rects,W,H);
    var n={id:w.id,x:p.x,y:p.y,app:w.app,urgent:w.urgent,focused:w.id===frame.focus,group:(w.group||[]).filter(function(id){return id!==w.id}),clearance:p.clearance};nodes.push(n);lookup[w.id]=n;
    var routePoints=route(hub,p,rects,W,H);
    if(routePoints.length)paths.push({id:"root:"+w.id,kind:"root",points:routePoints,svg:organic(routePoints,rects,seed+hash(w.id),W,H)});
  });
  (frame.workspaces||[]).filter(function(w){return w.id>0&&w.id!==m.workspace;}).slice(0,12).forEach(function(w,i){portals.push({id:w.id,name:w.name,x:clamp(20+(i%Math.max(1,Math.floor((W-32)/92)))*92,8,W-88),y:H-26-Math.floor(i/Math.max(1,Math.floor((W-32)/92)))*35});});
  edges.slice(-LIMITS.links).reverse().forEach(function(e){var a=lookup[e.a],b=lookup[e.b];if(!a||!b||paths.length>=64)return;var pts=route(a,b,rects,W,H);if(pts.length)paths.push({id:e.a+":"+e.b,kind:e.kind,points:pts,svg:svg(pts)});});
  // Real compositor groups share a routed junction; never guessed by app class.
  nodes.forEach(function(n){(n.group||[]).forEach(function(id){var b=lookup[id];if(!b||n.id>=id||paths.length>=64)return;var pts=route(n,b,rects,W,H);if(pts.length)paths.push({id:"group:"+n.id+id,kind:"group",points:pts,svg:svg(pts)});});});
  var moves=[];
  if(previous)nodes.forEach(function(n){var old=(previous.windows||[]).filter(function(w){return w.id===n.id;})[0];if(old&&old.workspace!==m.workspace)moves.push(n);});
  // Departures terminate at the destination's labeled workspace portal.
  (previous&&previous.windows||[]).forEach(function(old){var current=(frame.windows||[]).filter(function(w){return w.id===old.id;})[0];if(old.monitor!==m.id||old.workspace!==m.workspace||!current||current.workspace===old.workspace)return;
    var portal=portals.filter(function(p){return p.id===current.workspace;})[0];if(!portal)return;
    var p={x:clamp(old.x-m.x-5,4,W-4),y:clamp(old.y-m.y+old.h/2,52,H-4)},pts=route(p,portal,rects,W,H);if(pts.length)paths.push({id:"move:"+old.id,kind:"move",points:pts,svg:svg(pts)});
  });
  paths=paths.slice(0,64);
  var filaments=[];
  paths.filter(function(p){return p.kind==="root";}).forEach(function(path){
    var h=hash(path.id+seed),count=Math.min(12,path.points.length*3);
    for(var i=0;i<count&&filaments.length<LIMITS.tendrils;i++){
      var t=(i+1)/(count+1),p=sample(path.points,t),q=sample(path.points,Math.min(1,t+0.01));
      var dx=Math.sign(q.x-p.x),dy=Math.sign(q.y-p.y),side=((h>>i)&1)?1:-1;
      var len=18+((h>>(i%16))%38),end={x:p.x-dy*side*len,y:p.y+dx*side*len};
      if(end.x<4||end.x>W-4||end.y<50||end.y>H-12||!clear(p,end,rects))continue;
      var bend={x:end.x+dx*7,y:end.y+dy*7};
      // Curves stay in a tested orthogonal corridor; with 4px obstacle padding.
      if(bend.x<2||bend.x>W-2||bend.y<50||bend.y>H-2||!clear(end,bend,rects))continue;
      filaments.push({x:bend.x,y:bend.y,svg:"M "+p.x+" "+p.y+" Q "+end.x+" "+end.y+" "+bend.x+" "+bend.y});
      var tip={x:bend.x-dy*side*8,y:bend.y+dx*side*8};
      if(filaments.length<LIMITS.tendrils&&clear(bend,tip,rects)&&tip.x>4&&tip.x<W-4&&tip.y>50&&tip.y<H-12)
        filaments.push({x:tip.x,y:tip.y,svg:"M "+bend.x+" "+bend.y+" Q "+end.x+" "+end.y+" "+tip.x+" "+tip.y});
    }
  });
  var junctionMap={};
  paths.filter(function(p){return p.kind==="root";}).forEach(function(p){p.points.forEach(function(v){var key=Math.round(v.x)+":"+Math.round(v.y);if(!junctionMap[key])junctionMap[key]={x:v.x,y:v.y,count:0};junctionMap[key].count++;});});
  var junctions=Object.keys(junctionMap).map(function(k){return junctionMap[k];}).filter(function(j){return j.count>1;}).slice(0,16);
  return {nodes:nodes,paths:paths,filaments:filaments,junctions:junctions,portals:portals,hub:hub,seed:seed,off:m.off,fullscreen:all.some(function(w){return w.fullscreen;}),workspace:m.workspace,rects:rects,omitted:Math.max(0,all.length-LIMITS.windows)};
}
