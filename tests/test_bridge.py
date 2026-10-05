import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('bridge',Path(__file__).parents[1]/'bridge.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class BridgeTests(unittest.TestCase):
  def test_privacy_bounds(self):
    c={'address':'0x123','at':[20,40],'size':[800,600],'class':'foot','title':'PRIVATE SECRET','workspace':{'id':1},'monitor':0,'grouped':[]}
    value=b.normalize([c]*90,[{'id':0,'name':'DP-1','x':0,'y':0,'width':2000,'height':1400,'scale':2,'activeWorkspace':{'id':1}}],[{'id':1,'name':'1'}],c)
    self.assertEqual(len(value['windows']),48)
    self.assertNotIn('PRIVATE',str(value));self.assertNotIn('title',str(value))
    self.assertEqual(value['monitors'][0]['width'],1000)
  def test_seed_only_persistence(self):
    with tempfile.TemporaryDirectory() as tmp,patch.dict(b.os.environ,{'XDG_STATE_HOME':tmp}):
      state=b.load_state();b.save_state(state);self.assertEqual(state,b.load_state())
      self.assertEqual(set(state),{'seeds','paused','reducedMotion'})
      self.assertEqual(b.state_path().stat().st_mode&0o777,0o600)
  def test_stale_and_injection_focus(self):
    with patch.object(b,'query',return_value=[]),patch.object(b.subprocess,'run') as dispatch:
      for address in ['0x1','$(touch /tmp/no)','0x12;exec']:
        with patch.object(b.sys,'argv',['bridge','focus',address]):b.main()
      dispatch.assert_not_called()
  def test_live_focus(self):
    with patch.object(b,'query',return_value=[{'address':'0x1','mapped':True}]),patch.object(b.subprocess,'run') as dispatch,patch.object(b.sys,'argv',['bridge','focus','0x1']):
      b.main();self.assertEqual(dispatch.call_args.args[0],['hyprctl','dispatch','focuswindow','address:0x1'])
  def test_malformed_records(self):
    value=b.normalize([None,{}, {'address':'0x1','at':[0],'size':[20,20]}, {'address':'0x2','at':[0,float('nan')],'size':[20,20]}], [None,{}, {'id':0,'name':'x','x':0,'y':0,'width':100,'height':100,'scale':0}], [None,{}],None)
    self.assertEqual(value,{'windows':[],'focus':'','monitors':[],'workspaces':[]})
  def test_maximized_is_not_true_fullscreen(self):
    c={'address':'0x1','at':[9,44],'size':[1902,1027],'workspace':{'id':1},'monitor':0}
    for mode,expected in [(0,False),(1,False),(2,True),(False,False),(True,True)]:
      result=b.normalize([{**c,'fullscreen':mode,'fullscreenClient':2}],[],[],{})
      self.assertEqual(result['windows'][0]['fullscreen'],expected,(mode,expected))
  def test_rotated_scale(self):
    result=b.normalize([], [{'id':0,'name':'DP','x':0,'y':0,'width':1920,'height':1080,'scale':2,'transform':1}],[],{})
    self.assertEqual(result['monitors'][0]['width'],540)
    self.assertEqual(result['monitors'][0]['height'],960)
if __name__=='__main__':unittest.main()
