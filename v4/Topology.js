// Mycelium v4 geometry. Pure and bounded.
// Roots live on SEAMS: the lines where tiled windows meet each other and the
// screen edge. Seams exist at every gap size, including zero, so this works on
// any tiling layout. Each window side's seam sits in the middle of the space it
// faces; with no space it sits on the shared border line.
var LIMITS = {windows: 24, coords: 128, visits: 8000, junctions: 32, urgent: 4, tiles: 24, hops: 12};
var REACH = 64;
function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
function hash(s) { var h=2166136261; s=String(s); for(var i=0;i<s.length;i++) h=Math.imul(h^s.charCodeAt(i),16777619); return h>>>0; }
// Strict interior test with padding: a point on a window's edge is not inside.
function inside(p, r, pad) { pad=pad||0; return p.x>r.x+pad && p.x<r.x+r.w-pad && p.y>r.y+pad && p.y<r.y+r.h-pad; }
function overlap(a0,a1,b0,b1) { return Math.min(a1,b1)-Math.max(a0,b0); }
function round2(v) { return Math.round(v*2)/2; }
function unique(a) { return a.sort(function(x,y){return x-y;}).filter(function(v,i,s){return !i || v!==s[i-1];}); }

// Distance from each side of each rectangle to the nearest window it faces.
// null means nothing faces that side within REACH. A side that another tiled
// window overlaps is "open": there is no seam there to draw on.
function facing(rects) {
  return rects.map(function(r) {
    var s={l:null,r:null,t:null,b:null},open={l:false,r:false,t:false,b:false};
    function take(k,d,covers){ if(d<-1){ if(covers) open[k]=true; return; } if(d<REACH) s[k]=s[k]===null?d:Math.min(s[k],d); }
    rects.forEach(function(q) {
      if(q===r) return;
      if(overlap(r.y,r.y+r.h,q.y,q.y+q.h)>1) { take("l",r.x-(q.x+q.w),q.x<r.x); take("r",q.x-(r.x+r.w),q.x+q.w>r.x+r.w); }
      if(overlap(r.x,r.x+r.w,q.x,q.x+q.w)>1) { take("t",r.y-(q.y+q.h),q.y<r.y); take("b",q.y-(r.y+r.h),q.y+q.h>r.y+r.h); }
    });
    s.open=open;return s;
  });
}
// Per-side insets. Facing sides split the gap evenly, so neighbours' seams
// coincide. A side facing the screen edge sits in the middle of its margin.
// Sides flush with or beyond the screen edge (scrolling layouts) stay open:
// a line there could only land on the window itself.
var OUTER_CAP = 12;
function insets(rects, W, H, top, fixedOuter) {
  var faces=facing(rects);
  return rects.map(function(r,i) {
    var s=faces[i],open=s.open,out={open:open},margins={l:r.x,r:W-(r.x+r.w),t:r.y-top,b:H-(r.y+r.h)};
    ["l","r","t","b"].forEach(function(k) {
      if(open[k]) { out[k]=0; return; }
      if(s[k]!==null) { out[k]=clamp(Math.max(0,s[k])/2,0,REACH/2); return; }
      if(fixedOuter!==undefined) { out[k]=fixedOuter; return; }
      if(margins[k]<1) { open[k]=true; out[k]=0; return; }
      out[k]=Math.min(margins[k]/2,OUTER_CAP);
    });
    return out;
  });
}
// Snap near-identical coordinates together so shared seams merge exactly.
function snapper(values) {
  var sorted=unique(values.map(round2)),groups=[];
  sorted.forEach(function(v){ var g=groups[groups.length-1]; if(g&&v-g[g.length-1]<=1.25) g.push(v); else groups.push([v]); });
  var map={};groups.forEach(function(g){ var rep=round2(g.reduce(function(a,b){return a+b;},0)/g.length); g.forEach(function(v){map[v]=rep;}); });
  return function(v){ var k=round2(v); return map[k]!==undefined?map[k]:k; };
}

// The seam graph for one output. Returns frames per window, visible grid
// edges, junction knots and a combined SVG path for the quiet network.
function seams(tiled, occluders, W, H, top, fixedOuter) {
  var inset=insets(tiled,W,H,top,fixedOuter),frames=[];
  tiled.forEach(function(r,i){
    var s=inset[i];
    var o=s.open;
    frames.push({id:r.id,rect:r,inset:s,open:o,
      x0:o.l?r.x:clamp(r.x-s.l,0.5,W-0.5),x1:o.r?r.x+r.w:clamp(r.x+r.w+s.r,0.5,W-0.5),
      y0:o.t?r.y:clamp(r.y-s.t,0.5,H-0.5),y1:o.b?r.y+r.h:clamp(r.y+r.h+s.b,0.5,H-0.5)});
  });
  var occ=occluders.map(function(r){return {x:r.x-1.5,y:r.y-1.5,w:r.w+3,h:r.h+3};});
  var sx=snapper(frames.map(function(f){return f.x0;}).concat(frames.map(function(f){return f.x1;})));
  var sy=snapper(frames.map(function(f){return f.y0;}).concat(frames.map(function(f){return f.y1;})));
  frames.forEach(function(f){f.x0=sx(f.x0);f.x1=sx(f.x1);f.y0=sy(f.y0);f.y1=sy(f.y1);});
  var xs=[],ys=[];
  frames.forEach(function(f){xs.push(f.x0,f.x1);ys.push(f.y0,f.y1);});
  occ.forEach(function(o){xs.push(round2(o.x),round2(o.x+o.w));ys.push(round2(o.y),round2(o.y+o.h));});
  xs=unique(xs);ys=unique(ys);
  if(xs.length>LIMITS.coords||ys.length>LIMITS.coords) return {frames:frames,edges:[],junctions:[],svg:"",xs:[],ys:[]};
  var xi={},yi={};xs.forEach(function(v,i){xi[v]=i;});ys.forEach(function(v,i){yi[v]=i;});
  var edges={};
  function add(key,a,b,id){ var e=edges[key]; if(!e) e=edges[key]={a:a,b:b,owners:[]}; if(e.owners.indexOf(id)<0) e.owners.push(id); }
  frames.forEach(function(f){
    var i0=xi[f.x0],i1=xi[f.x1],j0=yi[f.y0],j1=yi[f.y1];
    for(var i=i0;i<i1;i++){ if(!f.open.t) add("h:"+i+":"+j0,{x:xs[i],y:f.y0},{x:xs[i+1],y:f.y0},f.id); if(!f.open.b) add("h:"+i+":"+j1,{x:xs[i],y:f.y1},{x:xs[i+1],y:f.y1},f.id); }
    for(var j=j0;j<j1;j++){ if(!f.open.l) add("v:"+i0+":"+j,{x:f.x0,y:ys[j]},{x:f.x0,y:ys[j+1]},f.id); if(!f.open.r) add("v:"+i1+":"+j,{x:f.x1,y:ys[j]},{x:f.x1,y:ys[j+1]},f.id); }
  });
  var list=[],degree={},svg="";
  Object.keys(edges).forEach(function(k){
    var e=edges[k],mid={x:(e.a.x+e.b.x)/2,y:(e.a.y+e.b.y)/2};
    if(occ.some(function(o){return inside(mid,o);})) return;
    e.key=k;list.push(e);
    [e.a,e.b].forEach(function(p){var n=p.x+":"+p.y;degree[n]=(degree[n]||0)+1;});
    svg+="M "+e.a.x+" "+e.a.y+" L "+e.b.x+" "+e.b.y+" ";
  });
  // Knots only where three or more seams meet: the T and X joints of a layout.
  var junctions=Object.keys(degree).filter(function(n){return degree[n]>=3;}).slice(0,LIMITS.junctions).map(function(n){var p=n.split(":");return {x:+p[0],y:+p[1]};});
  return {frames:frames,edges:list,junctions:junctions,svg:svg.trim(),xs:xs,ys:ys};
}

// Shortest path along visible seams between the frames of two windows.
function travel(net, fromId, toId) {
  var adj={};
  function key(p){return p.x+":"+p.y;}
  net.edges.forEach(function(e){ var a=key(e.a),b=key(e.b),w=Math.abs(e.a.x-e.b.x)+Math.abs(e.a.y-e.b.y);
    (adj[a]=adj[a]||[]).push([b,w,e.b]);(adj[b]=adj[b]||[]).push([a,w,e.a]); });
  var from={},to={},points={};
  net.edges.forEach(function(e){ [e.a,e.b].forEach(function(p){points[key(p)]=p;
    if(e.owners.indexOf(fromId)>=0) from[key(p)]=p; if(e.owners.indexOf(toId)>=0) to[key(p)]=p; }); });
  var fk=Object.keys(from),tk=Object.keys(to);
  if(!fk.length||!tk.length) return [];
  // Adjacent windows share a seam; no spark is needed, the root just grows.
  if(fk.some(function(k){return to[k]!==undefined;})) return [];
  var dist={},prev={},queue=[],visits=0;
  fk.forEach(function(k){dist[k]=0;queue.push([0,k]);});
  while(queue.length && visits++<LIMITS.visits) {
    queue.sort(function(a,b){return b[0]-a[0];});
    var item=queue.pop(),d=item[0],n=item[1];
    if(dist[n]!==d) continue;
    if(to[n]!==undefined) { var path=[],cur=n; while(cur!==undefined){path.unshift(points[cur]);cur=prev[cur];} return simplify(path); }
    (adj[n]||[]).forEach(function(nb){ var nd=d+nb[1]; if(dist[nb[0]]===undefined||nd<dist[nb[0]]){dist[nb[0]]=nd;prev[nb[0]]=n;queue.push([nd,nb[0]]);} });
  }
  return [];
}
function simplify(points) {
  return points.filter(function(p,i,s){return !i||i===s.length-1||!((s[i-1].x===p.x&&p.x===s[i+1].x)||(s[i-1].y===p.y&&p.y===s[i+1].y));});
}

// A window's seam frame as a closed polyline, parameterised by arc length.
// Waviness only uses the room its side actually has (R7).
function perimeter(frame, seed) {
  var f=frame,s=f.inset,corners=[{x:f.x0,y:f.y0},{x:f.x1,y:f.y0},{x:f.x1,y:f.y1},{x:f.x0,y:f.y1}];
  // Waviness and glow split the room beside the line: amplitude plus glow
  // half-width plus core half-width never exceeds the side's inset.
  var open=[s.open.t,s.open.r,s.open.b,s.open.l];
  var amps=[s.t,s.r,s.b,s.l].map(function(v,k){return open[k]?0:Math.max(0,Math.min(6,(v-1.5)/2));});
  var pts=[];
  for(var side=0;side<4;side++) {
    var a=corners[side],b=corners[(side+1)%4],len=Math.hypot(b.x-a.x,b.y-a.y),amp=amps[side];
    var nx=-(b.y-a.y)/(len||1),ny=(b.x-a.x)/(len||1);
    pts.push({x:a.x,y:a.y,side:side});
    if(!len) continue;
    // Points just past each corner keep corner smoothing off window interiors.
    var near=Math.min(2,len/4);
    pts.push({x:a.x+(b.x-a.x)*near/len,y:a.y+(b.y-a.y)*near/len,side:side});
    var steps=amp>0?Math.max(1,Math.round(len/24)):1;
    for(var k=1;k<steps;k++){
      var t=k/steps,o=amp*(((hash(seed+":"+side+":"+k)%1000)/1000)*2-1);
      pts.push({x:a.x+(b.x-a.x)*t+nx*o,y:a.y+(b.y-a.y)*t+ny*o,side:side});
    }
    pts.push({x:b.x-(b.x-a.x)*near/len,y:b.y-(b.y-a.y)*near/len,side:side});
  }
  pts.push({x:corners[0].x,y:corners[0].y});
  var cum=[0];
  for(var i=1;i<pts.length;i++) cum.push(cum[i-1]+Math.hypot(pts[i].x-pts[i-1].x,pts[i].y-pts[i-1].y));
  return {points:pts,cum:cum,length:cum[cum.length-1],open:open,wavy:amps.some(function(v){return v>0;})};
}
function at(per, s) {
  var P=per.length; s=((s%P)+P)%P;
  for(var i=1;i<per.cum.length;i++) if(s<=per.cum[i]) { var l=per.cum[i]-per.cum[i-1],f=l?(s-per.cum[i-1])/l:0; return {x:per.points[i-1].x+(per.points[i].x-per.points[i-1].x)*f,y:per.points[i-1].y+(per.points[i].y-per.points[i-1].y)*f}; }
  return per.points[per.points.length-1];
}
// Arc length of the perimeter point nearest p.
function nearest(per, p) {
  var best=0,bd=1e18;
  for(var i=1;i<per.points.length;i++) {
    var a=per.points[i-1],b=per.points[i],dx=b.x-a.x,dy=b.y-a.y,l2=dx*dx+dy*dy,t=l2?clamp(((p.x-a.x)*dx+(p.y-a.y)*dy)/l2,0,1):0;
    var q={x:a.x+dx*t,y:a.y+dy*t},d=Math.hypot(q.x-p.x,q.y-p.y);
    if(d<bd){bd=d;best=per.cum[i-1]+(per.cum[i]-per.cum[i-1])*t;}
  }
  return best;
}
// Parameter interval [t0,t1] of segment p->q inside rectangle r (Liang-Barsky).
function within(p, q, r) {
  var t0=0,t1=1,dx=q.x-p.x,dy=q.y-p.y,checks=[[-dx,p.x-r.x],[dx,r.x+r.w-p.x],[-dy,p.y-r.y],[dy,r.y+r.h-p.y]];
  for(var i=0;i<4;i++){ var pp=checks[i][0],qq=checks[i][1];
    if(pp===0){ if(qq<0) return null; continue; }
    var t=qq/pp; if(pp<0){ if(t>t1) return null; if(t>t0) t0=t; } else { if(t<t0) return null; if(t<t1) t1=t; } }
  return t1>t0?[t0,t1]:null;
}
// Visible sub-segments of p->q once every occluder is cut out exactly.
function uncovered(p, q, occluders, pad) {
  var cuts=[];pad=pad===undefined?1.5:pad;
  (occluders||[]).forEach(function(o){ var c=within(p,q,{x:o.x-pad,y:o.y-pad,w:o.w+2*pad,h:o.h+2*pad}); if(c) cuts.push(c); });
  if(!cuts.length) return [[p,q]];
  cuts.sort(function(a,b){return a[0]-b[0];});
  var out=[],t=0;
  function lerp(v){return {x:p.x+(q.x-p.x)*v,y:p.y+(q.y-p.y)*v};}
  cuts.forEach(function(c){ if(c[0]>t) out.push([lerp(t),lerp(c[0])]); t=Math.max(t,c[1]); });
  if(t<1) out.push([lerp(t),q]);
  return out;
}
// Runs of visible polyline between arc lengths a and b (b may pass P once).
// Occluders cut runs exactly, so nothing is drawn across a floating window.
function runs(per, a, b, occluders, pad) {
  var P=per.length,out=[],run=null;
  if(!(P>0)||b<=a) return out;
  function emit(p,q,side){
    var parts=per.open&&per.open[side]?[]:uncovered(p,q,occluders,pad);
    parts.forEach(function(part,i){
      var joined=run&&i===0&&Math.abs(part[0].x-p.x)<1e-6&&Math.abs(part[0].y-p.y)<1e-6;
      if(!joined){ if(run&&run.length>1) out.push(run); run=[part[0]]; }
      run.push(part[1]);
    });
    var last=parts[parts.length-1];
    if(!parts.length||Math.abs(last[1].x-q.x)>1e-6||Math.abs(last[1].y-q.y)>1e-6){ if(run&&run.length>1) out.push(run); run=null; }
  }
  for(var lap=0;lap<2;lap++) {
    var base=lap*P;
    for(var i=1;i<per.points.length;i++) {
      var s0=per.cum[i-1]+base,s1=per.cum[i]+base,lo=Math.max(a,s0),hi=Math.min(b,s1);
      if(hi<=lo) continue;
      emit(at(per,lo),at(per,hi),per.points[i-1].side);
    }
  }
  if(run&&run.length>1) out.push(run);
  return out;
}
// Smooth through midpoints when wavy, straight otherwise.
function svg(lines, smooth) {
  return lines.map(function(pts){
    if(!pts.length) return "";
    var out="M "+pts[0].x.toFixed(1)+" "+pts[0].y.toFixed(1);
    if(!smooth||pts.length<3){ for(var i=1;i<pts.length;i++) out+=" L "+pts[i].x.toFixed(1)+" "+pts[i].y.toFixed(1); return out; }
    for(var j=1;j<pts.length-1;j++){ var m={x:(pts[j].x+pts[j+1].x)/2,y:(pts[j].y+pts[j+1].y)/2}; out+=" Q "+pts[j].x.toFixed(1)+" "+pts[j].y.toFixed(1)+" "+m.x.toFixed(1)+" "+m.y.toFixed(1); }
    var last=pts[pts.length-1]; return out+" L "+last.x.toFixed(1)+" "+last.y.toFixed(1);
  }).join(" ");
}
// Root grown around a frame from arc length s0, covering fraction t (0..1).
function grown(per, s0, t, occluders, pad) {
  var half=clamp(t,0,1)*per.length/2;
  if(half<=0) return "";
  if(t>=0.999) return svg(runs(per,0,per.length,occluders,pad),per.wavy);
  var a=s0-half; if(a<0) a+=per.length;
  return svg(runs(per,a,a+half*2,occluders,pad),per.wavy);
}
function sample(points,t) {
  var lengths=[],total=0;
  for(var i=1;i<points.length;i++){var l=Math.hypot(points[i].x-points[i-1].x,points[i].y-points[i-1].y);lengths.push(l);total+=l;}
  var target=clamp(t,0,1)*total;
  for(var j=0;j<lengths.length;j++){if(target<=lengths[j]){var f=lengths[j]?target/lengths[j]:0;return {x:points[j].x+(points[j+1].x-points[j].x)*f,y:points[j].y+(points[j+1].y-points[j].y)*f};}target-=lengths[j];}
  return points.length?points[points.length-1]:{x:0,y:0};
}
function center(r){return {x:r.x+r.w/2,y:r.y+r.h/2};}
// Smallest inset among a frame's drawn sides; glow and waviness fit inside it.
function roomOf(f){ var v=[];["l","r","t","b"].forEach(function(k){ if(!f.inset.open[k]) v.push(f.inset[k]); }); return v.length?Math.min.apply(null,v):0; }
// Cut distance around occluders: core half-width, glow half-width, one pixel spare.
function padFor(glow){ return 1.75+(glow>0?glow/2:0); }

// Everything the ambient layer needs for one output.
function graph(frame, name, pulseFrom, pulseTo, W, H) {
  var m=(frame.monitors||[]).filter(function(m){return m.name===name;})[0];
  var empty={frames:[],edges:[],junctions:[],svg:"",urgent:[],focus:null,travel:[],rects:[],occluders:[]};
  if(!m) { empty.off=true; return empty; }
  if(W<80||H<80) { empty.off=m.off; return empty; }
  var all=(frame.windows||[]).filter(function(w){return w.monitor===m.id && w.workspace===m.workspace;});
  var local=all.map(function(w){return {id:w.id,x:w.x-m.x,y:w.y-m.y,w:w.w,h:w.h,floating:!!w.floating,urgent:!!w.urgent,fullscreen:!!w.fullscreen};});
  var top=(m.reserved&&m.reserved[1])||0;
  // Windows entirely off this output (scrolling layouts) are not on screen.
  local=local.filter(function(r){return r.x+r.w>0&&r.x<W&&r.y+r.h>top&&r.y<H;});
  var tiledAll=local.filter(function(r){return !r.floating;}),tiled=tiledAll.slice(0,LIMITS.windows);
  // Floating windows, windows past the bound and an open scratchpad sit above
  // the tiled layer: nothing is drawn across them.
  var occluders=local.filter(function(r){return r.floating;}).concat(tiledAll.slice(LIMITS.windows));
  if(m.special) (frame.windows||[]).forEach(function(w){ if(w.monitor===m.id&&w.workspace===m.special) occluders.push({id:w.id,x:w.x-m.x,y:w.y-m.y,w:w.w,h:w.h,floating:true}); });
  var net=seams(tiled,occluders,W,H,top);
  var seeds=frame.settings&&frame.settings.seeds||[73217],seed=seeds[Math.abs(m.workspace)%seeds.length];
  var byId={};net.frames.forEach(function(f){byId[f.id]=f;});
  var focus=null,path=[];
  var target=byId[frame.focus];
  if(target) {
    var per=perimeter(target,seed+":"+target.id);
    var prevFrame=byId[pulseFrom],origin;
    if(prevFrame && pulseTo===target.id) {
      path=travel(net,pulseFrom,target.id);
      // Neighbours: grow from the middle of the seam they share.
      var shared=net.edges.filter(function(e){return e.owners.indexOf(pulseFrom)>=0&&e.owners.indexOf(target.id)>=0;});
      if(path.length) origin=path[path.length-1];
      else if(shared.length) {
        var xs=[],ys=[];shared.forEach(function(e){xs.push(e.a.x,e.b.x);ys.push(e.a.y,e.b.y);});
        origin={x:(Math.min.apply(null,xs)+Math.max.apply(null,xs))/2,y:(Math.min.apply(null,ys)+Math.max.apply(null,ys))/2};
      } else origin=center(prevFrame.rect);
    } else origin={x:W/2,y:top};
    var room=roomOf(target),glow=room>=2.5?Math.min(8,room-1.5):-1,pad=padFor(glow);
    focus={id:target.id,perimeter:per,start:nearest(per,origin),full:grown(per,0,1,occluders,pad),inset:room,glow:glow,pad:pad};
  }
  var urgent=net.frames.filter(function(f){return f.rect.urgent;}).slice(0,LIMITS.urgent).map(function(f){
    var per=perimeter(f,seed+":u:"+f.id),room=roomOf(f),glow=room>=2.5?Math.min(8,room-1.5):-1;
    return {id:f.id,svg:grown(per,0,1,occluders,padFor(glow)),glow:glow};});
  var minInset=net.frames.reduce(function(v,f){return Math.min(v,roomOf(f));},REACH);
  return {frames:net.frames,edges:net.edges,junctions:net.junctions,svg:net.svg,urgent:urgent,focus:focus,travel:path,minInset:net.frames.length?minInset:0,
    rects:local,occluders:occluders,seed:seed,off:m.off,fullscreen:all.some(function(w){return w.fullscreen;}),workspace:m.workspace,
    omitted:Math.max(0,local.filter(function(r){return !r.floating;}).length-LIMITS.windows)};
}

// Trace map: every workspace as a scaled miniature of its monitor.
function forest(frame, hops, area, page, minTile) {
  var monitors=frame.monitors||[],focusedMon=monitors.filter(function(m){return m.focused;})[0]||monitors[0];
  var current={};monitors.forEach(function(m){current[m.workspace]=true;});
  var spaces=(frame.workspaces||[]).filter(function(w){return w.id>0;}).sort(function(a,b){return a.id-b.id;}).slice(0,LIMITS.tiles);
  var aspect=focusedMon&&focusedMon.height>0?focusedMon.width/focusedMon.height:16/9;
  var gap=28,label=20,n=spaces.length;
  // Outer gutter seams need half a gutter inside the area.
  area={x:area.x+gap/2,y:area.y+gap/2,w:Math.max(1,area.w-gap),h:Math.max(1,area.h-gap)};
  minTile=minTile||150;
  function fit(count){
    var best={w:0,c:1,r:1};
    for(var c=1;c<=Math.max(1,count);c++){
      var r=Math.ceil(count/c),cw=(area.w-(c-1)*gap)/c,ch=(area.h-(r-1)*gap)/r-label,w=Math.min(cw,ch*aspect);
      if(w>best.w) best={w:w,c:c,r:r};
    }
    return best;
  }
  var layout=fit(n),perPage=n,pages=1;
  if(n&&layout.w<minTile) {
    var c=Math.max(1,Math.floor((area.w+gap)/(minTile+gap))),r=Math.max(0,Math.floor((area.h+gap)/(minTile/aspect+label+gap)));
    perPage=Math.max(1,c*r);pages=Math.max(1,Math.ceil(n/perPage));
  }
  page=clamp(page||0,0,pages-1);
  var shown=spaces.slice(page*perPage,(page+1)*perPage);
  layout=fit(shown.length);
  var tw=Math.max(1,Math.floor(layout.w)),th=Math.max(1,Math.floor(tw/aspect));
  var gridW=layout.c*tw+(layout.c-1)*gap,gridH=layout.r*(th+label)+(layout.r-1)*gap;
  var ox=area.x+(area.w-gridW)/2,oy=area.y+Math.max(0,(area.h-gridH)/2);
  var tiles=shown.map(function(ws,i){
    var col=i%layout.c,row=Math.floor(i/layout.c);
    var mon=monitors.filter(function(m){return m.id===ws.monitor;})[0]||focusedMon||{x:0,y:0,width:tw,height:th};
    var x=ox+col*(tw+gap),y=oy+row*(th+label+gap)+label,sx=tw/Math.max(1,mon.width),sy=th/Math.max(1,mon.height);
    var wins=(frame.windows||[]).filter(function(w){return w.workspace===ws.id;}).sort(function(a,b){return (a.floating?1:0)-(b.floating?1:0);}).map(function(w){
      var r=w.fullscreen?{x:0,y:0,w:tw,h:th}:{x:clamp((w.x-mon.x)*sx,0,tw-4),y:clamp((w.y-mon.y)*sy,0,th-4),w:0,h:0};
      if(!w.fullscreen){r.w=clamp(w.w*sx,4,tw-r.x);r.h=clamp(w.h*sy,4,th-r.y);}
      return {id:w.id,app:w.app,x:r.x,y:r.y,w:r.w,h:r.h,focused:w.id===frame.focus,urgent:!!w.urgent,floating:!!w.floating};
    });
    return {id:ws.id,name:ws.name,x:x,y:y,w:tw,h:th,current:!!current[ws.id],focused:!!(focusedMon&&focusedMon.workspace===ws.id),
      urgent:wins.some(function(w){return w.urgent;}),windows:wins};
  });
  // The map has seams too: the gutters between tiles. Hop roots run along them,
  // exactly like roots on the desktop run along window seams.
  var blocks=tiles.map(function(t){return {id:String(t.id),x:t.x,y:t.y-label,w:t.w,h:t.h+label};});
  var net=seams(blocks,[],area.x+area.w+gap,area.y+area.h+gap,area.y-gap,gap/2);
  var known={};tiles.forEach(function(t){known[t.id]=true;});
  var pairs={},order=[];
  (hops||[]).slice(-LIMITS.hops).forEach(function(h){
    var a=Math.min(h.a,h.b),b=Math.max(h.a,h.b),k=a+":"+b;
    if(!known[a]||!known[b]||a===b) return;
    if(!pairs[k]){pairs[k]={a:a,b:b,count:0};order.push(k);}
    pairs[k].count++;
    order.forEach(function(o){pairs[o].last=o===k;});
  });
  var roots=order.map(function(k){
    var p=pairs[k],path=travel(net,String(p.a),String(p.b)),d;
    var A=String(p.a),B=String(p.b);
    if(path.length) d=svg([path],false);
    else d=net.edges.filter(function(e){return e.owners.indexOf(A)>=0&&e.owners.indexOf(B)>=0;}).map(function(e){return "M "+e.a.x+" "+e.a.y+" L "+e.b.x+" "+e.b.y;}).join(" ");
    if(!d) {
      // Diagonal tiles touch only at a gutter crossing: an L along both seams.
      var fa=net.frames.filter(function(f){return f.id===A;})[0],fb=net.frames.filter(function(f){return f.id===B;})[0];
      var cx=[fa.x0,fa.x1].filter(function(x){return x===fb.x0||x===fb.x1;})[0],cy=[fa.y0,fa.y1].filter(function(y){return y===fb.y0||y===fb.y1;})[0];
      if(cx!==undefined&&cy!==undefined) d=svg([[{x:cx,y:(fa.y0+fa.y1)/2},{x:cx,y:cy},{x:(fb.x0+fb.x1)/2,y:cy}]],false);
    }
    return {id:k,svg:d,count:p.count,last:!!p.last};
  }).filter(function(r){return r.svg;});
  var soil=net.svg;
  return {tiles:tiles,roots:roots,soil:soil,page:page,pages:pages,perPage:perPage,count:n,columns:layout.c};
}
