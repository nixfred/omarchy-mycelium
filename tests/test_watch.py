"""Run the actual event loop against a disposable compositor socket.

No real windows, focus changes, desktop configuration, or credentials involved.
"""
import importlib.util
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WatchTests(unittest.TestCase):
  def test_event_stream_and_idle_resource_gate(self):
    with tempfile.TemporaryDirectory(prefix='mycelium-watch-') as tmp:
      work = Path(tmp)
      endpoint = work / 'hypr' / 'fixture'
      endpoint.mkdir(parents=True)
      server = socket.socket(socket.AF_UNIX)
      server.bind(str(endpoint / '.socket2.sock'))
      server.listen(1)
      server.settimeout(3)
      records = {'clients': [], 'monitors': [{'id': 0, 'name': 'fixture', 'x': 0,
        'y': 0, 'width': 1200, 'height': 800, 'activeWorkspace': {'id': 1}}],
        'workspaces': [{'id': 1}, {'id': 2}], 'activewindow': {}}
      data = work / 'records.json'
      queries = work / 'queries.jsonl'
      def save():
        staging = data.with_suffix('.tmp')
        staging.write_text(json.dumps(records))
        staging.replace(data)
      save()
      wrapper = work / 'watch.py'
      wrapper.write_text('''import importlib.util,json,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('bridge',ROOT/'bridge.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def query(kind):
 with QUERIES.open('a') as log:log.write(json.dumps([time.monotonic(),kind])+'\\n')
 return json.loads(DATA.read_text())[kind]
b.query=query
b.watch()
'''.replace('ROOT', 'Path('+repr(str(ROOT))+')')
        .replace('QUERIES', 'Path('+repr(str(queries))+')')
        .replace('DATA', 'Path('+repr(str(data))+')'))
      env = {**os.environ, 'XDG_RUNTIME_DIR': tmp, 'HYPRLAND_INSTANCE_SIGNATURE': 'fixture',
             'XDG_STATE_HOME': str(work / 'state')}
      child = subprocess.Popen([sys.executable, str(wrapper)], env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      connection = None
      buffer = b''
      frames = []
      def frame():
        nonlocal buffer
        deadline = time.monotonic() + 3
        while b'\n' not in buffer:
          remaining = deadline - time.monotonic()
          self.assertGreater(remaining, 0, 'Bridge did not emit a frame')
          self.assertTrue(select.select([child.stdout], [], [], remaining)[0])
          chunk = os.read(child.stdout.fileno(), 65536)
          if not chunk: self.fail(child.stderr.read().decode())
          buffer += chunk
        line, buffer = buffer.split(b'\n', 1)
        result = json.loads(line)
        frames.append(result)
        return result
      def event(name):
        save()
        connection.sendall((name+'>>ignored private event payload\n').encode())
        return frame()
      def query_log():
        return [json.loads(line) for line in queries.read_text().splitlines()]
      try:
        connection, _ = server.accept()
        self.assertEqual(frame()['windows'], [])
        # select must drain batched commands and assemble fragmented commands.
        child.stdin.write(b'idle\nresync\n'); child.stdin.flush()
        self.assertEqual(frame()['windows'], [])
        child.stdin.write(b'resy'); child.stdin.flush()
        time.sleep(0.04)
        child.stdin.write(b'nc\n'); child.stdin.flush()
        self.assertEqual(frame()['windows'], [])
        client = {'address': '0xabc', 'at': [100, 200], 'size': [300, 200],
          'monitor': 0, 'workspace': {'id': 1}, 'class': 'fixture-app',
          'title': 'PRIVATE CONTENT', 'mapped': True}
        records['clients'] = [client]
        self.assertEqual(event('openwindow')['windows'][0]['id'], '0xabc')
        connection.sendall(b'urgent>>abc\n')
        self.assertTrue(frame()['windows'][0]['urgent'])
        records['activewindow'] = {'address': '0xabc'}
        focused = event('activewindowv2')
        self.assertEqual(focused['focus'], '0xabc')
        self.assertFalse(focused['windows'][0]['urgent'])
        client['grouped'] = ['0xdef']
        self.assertEqual(event('togglegroup')['windows'][0]['group'], ['0xdef'])
        client['workspace']['id'] = 2
        self.assertEqual(event('movewindowv2')['windows'][0]['workspace'], 2)
        client['fullscreen'] = 2
        self.assertTrue(event('fullscreen')['windows'][0]['fullscreen'])
        records['monitors'][0]['dpmsStatus'] = False
        self.assertTrue(event('configreloaded')['monitors'][0]['off'])
        # First probe may run immediately; subsequent unchanged probes are 2 Hz.
        active_start = time.monotonic()
        child.stdin.write(b'active\n'); child.stdin.flush()
        time.sleep(1.12)
        child.stdin.write(b'idle\n'); child.stdin.flush()
        time.sleep(0.08)
        probes = [stamp for stamp, kind in query_log() if kind == 'clients' and stamp >= active_start]
        self.assertGreaterEqual(len(probes), 3)
        self.assertLessEqual(len(probes), 4)  # one changed-geometry snapshot allowed
        gaps = [b-a for a,b in zip(probes, probes[1:]) if b-a > 0.01]
        self.assertTrue(gaps and all(g >= 0.48 for g in gaps), gaps)
        count = len(query_log())
        time.sleep(0.72)
        self.assertEqual(len(query_log()), count, 'Idle polling continued')
        # Drain an initial changed-geometry snapshot, if queued.
        if buffer or select.select([child.stdout], [], [], 0)[0]: frame()
        records['clients'] = []; records['activewindow'] = {}
        self.assertEqual(event('closewindow')['windows'], [])
        # Continuous irrelevant payload is ignored, and event bursts coalesce.
        before = len(query_log())
        connection.sendall(b'openwindow>>abc\n' * 100)
        self.assertEqual(frame()['windows'], [])
        self.assertEqual(len(query_log()) - before, 4)
        self.assertNotIn('PRIVATE', json.dumps(frames))
        child.stdin.write(b'resync'); child.stdin.flush(); child.stdin.close()
        self.assertEqual(frame()['windows'], [], 'Final EOF resync was lost')
        connection.close(); connection = None
        self.assertTrue(frame()['unavailable'])
        self.assertEqual(child.wait(timeout=3), 0)
      finally:
        if connection: connection.close()
        server.close()
        if child.poll() is None: child.terminate(); child.wait(timeout=3)
        for stream in (child.stdin, child.stdout, child.stderr): stream.close()


if __name__ == '__main__': unittest.main()
