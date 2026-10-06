// Exercise the actual QML resource predicates with adversarial gate combinations.
const fs = require('fs'), assert = require('assert');
const source = fs.readFileSync(__dirname + '/../v4/Service.qml', 'utf8');
const expression = source.match(/readonly property bool geometryActive: (.+)/)[1];
const gate = new Function('testMode','paused','reducedMotion','idle','unavailable','frame',
  'return (' + expression + ')');
const frame = {monitors:[{id:0,workspace:1,off:false}],windows:[]};
const enabled = (changes = {}, f = frame) => gate(false, false, false, {isIdle:false}, false, f);
assert(enabled());
for (const index of [0,1,4]) {
  const args = [false,false,false,{isIdle:false},false,frame]; args[index] = true;
  assert.equal(gate(...args), false, 'resource gate index '+index);
}
// Still keeps tracking geometry on purpose: seams sit on window borders and
// must follow a resize even when nothing animates.
assert.equal(gate(false,false,true,{isIdle:false},false,frame), true);
assert.equal(gate(false,false,false,{isIdle:true},false,frame), false);
assert.equal(enabled({}, {monitors:[],windows:[]}), false);
assert.equal(enabled({}, {monitors:[{...frame.monitors[0],off:true}],windows:[]}), false);
const full = {monitor:0,workspace:1,fullscreen:true};
assert.equal(enabled({}, {monitors:frame.monitors,windows:[full]}), false);
// A fullscreen app on a hidden workspace must not suspend a visible output.
assert.equal(enabled({}, {monitors:frame.monitors,windows:[{...full,workspace:2}]}), true);
// A second visible monitor keeps geometry active while the first is covered.
assert.equal(enabled({}, {monitors:[...frame.monitors,{id:1,workspace:2,off:false}],windows:[full]}), true);
const network = fs.readFileSync(__dirname + '/../v4/Network.qml', 'utf8');
const motionExpression = network.match(/readonly property bool motion: (.+)/)[1];
const motion = new Function('renderingEnabled','visible','controller','graph','return ('+motionExpression+')');
assert(motion(true,true,{animating:true},{off:false,fullscreen:false}));
for (const args of [[false,true,{animating:true},{}],[true,false,{animating:true},{}],
  [true,true,{animating:false},{}],[true,true,{animating:true},{off:true}],
  [true,true,{animating:true},{fullscreen:true}]]) assert.equal(motion(...args),false);
assert(source.includes('mask:Region {}') && source.includes('WlrKeyboardFocus.None'));
console.log('PASS QML geometry and render gates: test mode, paused, idle, still keeps geometry, outage, no output, off, fullscreen, hidden workspace, multi-output, hidden renderer');
