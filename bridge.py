#!/usr/bin/python3
"""Event-driven compositor bridge. Only normalized geometry/class leaves memory.

No titles, content, screenshots, keystrokes or activity history are collected.
The single state file contains only random visual seeds and visual preferences.
"""
import json
import math
import os
from pathlib import Path
import re
import select
import socket
import subprocess
import sys
import time

MAX_WINDOWS = 48
MAX_WORKSPACES = 24
EVENTS = {"openwindow", "closewindow", "activewindowv2", "movewindow", "movewindowv2",
          "workspace", "workspacev2", "focusedmon", "monitoradded", "monitoraddedv2",
          "monitorremoved", "fullscreen", "changefloatingmode", "togglegroup", "moveintogroup",
          "moveoutofgroup", "urgent", "configreloaded", "moveworkspace", "moveworkspacev2",
          "renameworkspace", "windowtitle", "minimized", "activelayout", "createworkspacev2",
          "destroyworkspacev2"}


def query(kind):
  result = subprocess.run(["hyprctl", "-j", kind], capture_output=True, text=True, timeout=3)
  if result.returncode:
    raise RuntimeError("Compositor query unavailable")
  return json.loads(result.stdout)


def normalize(clients, monitors, workspaces, active):
  clients = clients if isinstance(clients, list) else []
  monitors = monitors if isinstance(monitors, list) else []
  workspaces = workspaces if isinstance(workspaces, list) else []
  active = active if isinstance(active, dict) else {}
  def numeric(v):
    return type(v) in (int, float) and math.isfinite(v)
  def workspace(record):
    value = record.get("workspace", {})
    return value.get("id", 0) if isinstance(value, dict) and type(value.get("id", 0)) is int else 0
  windows = []
  for c in clients:
    if not isinstance(c, dict) or not c.get("mapped", True) or c.get("hidden"):
      continue
    address = str(c.get("address", ""))
    if not re.fullmatch(r"0x[0-9a-fA-F]+", address):
      continue
    at, size = c.get("at", []), c.get("size", [])
    if not isinstance(at, list) or not isinstance(size, list) or len(at) != 2 or len(size) != 2 or not all(numeric(v) for v in at + size) or min(size) <= 0:
      continue
    group = c.get("grouped", [])
    group = group if isinstance(group, list) else []
    # Hyprland internal enum: 0 normal, 1 maximized (still has gaps),
    # 2 true fullscreen. Older boolean feeds retain their true/false meaning.
    mode = c.get("fullscreen", 0)
    covered = mode is True or (type(mode) is int and mode == 2)
    windows.append({"id": address, "x": at[0], "y": at[1], "w": size[0], "h": size[1],
                    "app": str(c.get("class", ""))[:96], "workspace": workspace(c),
                    "monitor": c.get("monitor", -1), "urgent": bool(c.get("urgent", False)),
                    "fullscreen": covered, "floating": bool(c.get("floating", False)),
                    "group": [str(a) for a in group if re.fullmatch(r"0x[0-9a-fA-F]+", str(a))][:MAX_WINDOWS]})
    if len(windows) >= MAX_WINDOWS:
      break
  outputs = []
  for m in monitors[:16]:
    if not isinstance(m, dict) or not isinstance(m.get("name"), str) or type(m.get("id")) is not int or not all(numeric(m.get(k)) for k in ("x", "y", "width", "height")):
      continue
    scale = m.get("scale", 1)
    if not numeric(scale) or scale <= 0:
      continue
    transform = m.get("transform", 0)
    transform = transform if type(transform) is int else 0
    ws = m.get("activeWorkspace", {})
    # Reserved edges (the bar) as [left, top, right, bottom] logical pixels.
    reserved = m.get("reserved", [])
    reserved = [v for v in reserved if numeric(v)][:4] if isinstance(reserved, list) else []
    reserved = reserved if len(reserved) == 4 else [0, 0, 0, 0]
    special = m.get("specialWorkspace", {})
    outputs.append({"id": m["id"], "name": m["name"][:96], "x": m["x"], "y": m["y"],
                    "width": (m["height"] if transform % 2 else m["width"]) / scale,
                    "height": (m["width"] if transform % 2 else m["height"]) / scale,
                    "workspace": ws.get("id", 0) if isinstance(ws, dict) else 0,
                    "off": bool(m.get("disabled") or not m.get("dpmsStatus", True)), "transform": transform,
                    "focused": bool(m.get("focused", False)), "reserved": reserved,
                    # An open scratchpad (special workspace) covers the tiled layer.
                    "special": special.get("id", 0) if isinstance(special, dict) and type(special.get("id", 0)) is int else 0})
  return {"windows": windows, "focus": str(active.get("address", "")), "monitors": outputs,
          "workspaces": [{"id": w["id"], "name": str(w.get("name", w["id"]))[:48],
                          "monitor": w["monitorID"] if type(w.get("monitorID")) is int else -1}
                         for w in workspaces[:MAX_WORKSPACES] if isinstance(w, dict) and type(w.get("id")) is int]}


def snapshot():
  return normalize(query("clients"), query("monitors"), query("workspaces"), query("activewindow"))


def state_path():
  base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "mycelium"
  base.mkdir(mode=0o700, parents=True, exist_ok=True)
  return base / "visual.json"


def load_state():
  path = state_path()
  try:
    state = json.loads(path.read_text())
  except (OSError, ValueError):
    state = {}
  # A fixed bounded bank stays stable through workspace renumbering; no private names.
  seeds = state.get("seeds", [])
  if not isinstance(seeds, list) or len(seeds) != 32 or any(type(s) is not int for s in seeds):
    seeds = [int.from_bytes(os.urandom(4), "little") for _ in range(32)]
  return {"seeds": seeds, "paused": bool(state.get("paused", False)),
          "reducedMotion": bool(state.get("reducedMotion", False))}


def save_state(state):
  path = state_path()
  temp = path.with_suffix(".tmp")
  fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
  with os.fdopen(fd, "w") as out:
    json.dump(state, out)
  os.replace(temp, path)


def emit(value):
  print(json.dumps(value, separators=(",", ":")), flush=True)


def watch():
  state = load_state()
  save_state(state)
  signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
  runtime = os.environ.get("XDG_RUNTIME_DIR", "")
  if not signature or not runtime:
    emit({"unavailable": True, "settings": state})
    return
  sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
  sock.connect(f"{runtime}/hypr/{signature}/.socket2.sock")
  pending, due, buffer = True, time.monotonic(), b""
  command_buffer = b""
  inputs = [sock, sys.stdin]
  active, geometry_due, last_geometry = False, 0, None
  urgent_ids = set()
  while True:
    deadlines = ([due] if pending else []) + ([geometry_due] if active else [])
    timeout = max(0, min(deadlines) - time.monotonic()) if deadlines else None
    ready, _, _ = select.select(inputs, [], [], timeout)
    if sys.stdin in ready:
      # select() sees kernel bytes, not TextIOWrapper's prefetched lines. Drain
      # every complete command so coalesced idle/resync cannot strand a resync.
      commands = os.read(sys.stdin.fileno(), 4096)
      if not commands:
        # Preserve the final recovery request if the writer closes without \n.
        if command_buffer.strip() == b"resync":
          pending, due = True, time.monotonic()
        command_buffer = b""
        inputs.remove(sys.stdin)
        active = False
      else:
        command_buffer += commands
        lines = command_buffer.split(b"\n")
        command_buffer = lines.pop()[-1024:]
        for command in lines:
          if command.strip() == b"resync":
            pending, due = True, time.monotonic()
          else:
            active = command.strip() == b"active"
        geometry_due = time.monotonic()
    if sock in ready:
      data = sock.recv(65536)
      if not data:
        emit({"unavailable": True})
        return
      buffer += data
      lines = buffer.split(b"\n")
      buffer = lines.pop()[-65536:]
      for line in lines:
        event, _, payload = line.partition(b">>")
        if event == b"urgent":
          address = payload.decode(errors="ignore").split(",")[0]
          if not address.startswith("0x"):
            address = "0x" + address
          if re.fullmatch(r"0x[0-9a-fA-F]+", address):
            urgent_ids.add(address)
      if any(line.partition(b">>")[0].decode(errors="ignore") in EVENTS for line in lines):
        # Fixed deadline bounds snapshots at 8 Hz even under a continuous event stream.
        if not pending:
          due = time.monotonic() + 0.125
        pending = True
    if active and time.monotonic() >= geometry_due:
      # Hyprland emits no resize/move geometry event. Probe only while the native
      # compositor idle monitor says the user is active. No idle polling loop.
      geometry_due = time.monotonic() + 0.5
      try:
        geometry = [(c.get("address"), c.get("at"), c.get("size")) for c in query("clients")[:MAX_WINDOWS] if isinstance(c, dict)]
        if geometry != last_geometry:
          last_geometry = geometry
          if not pending:
            pending, due = True, time.monotonic()
      except (RuntimeError, ValueError, subprocess.TimeoutExpired):
        emit({"unavailable": True})
        return
    if pending and time.monotonic() >= due:
      try:
        frame = snapshot()
        # This Hyprland version has no clients[].urgent field. Its actual urgent
        # socket event sets a knot; focus clears urgency, and close drops it.
        urgent_ids.discard(frame["focus"])
        urgent_ids.intersection_update(w["id"] for w in frame["windows"])
        for window in frame["windows"]:
          window["urgent"] = window["urgent"] or window["id"] in urgent_ids
        frame["settings"] = state
        emit(frame)
      except (RuntimeError, ValueError, subprocess.TimeoutExpired):
        emit({"unavailable": True})
        return
      pending = False


def main():
  action = sys.argv[1] if len(sys.argv) > 1 else "watch"
  if action == "watch":
    watch()
  elif action == "settings":
    state = load_state()
    if len(sys.argv) == 4 and sys.argv[2] in ("paused", "reducedMotion"):
      state[sys.argv[2]] = sys.argv[3] == "true"
      save_state(state)
    emit(state)
  elif action == "preferences" and len(sys.argv) == 4:
    state = load_state()
    state.update(paused=sys.argv[2] == "true", reducedMotion=sys.argv[3] == "true")
    save_state(state)
  elif action == "focus" and len(sys.argv) == 3:
    address = sys.argv[2]
    # Live revalidation immediately before dispatch; vanished addresses do nothing.
    if re.fullmatch(r"0x[0-9a-fA-F]+", address) and any(c.get("address") == address and c.get("mapped", True) for c in query("clients")):
      subprocess.run(["hyprctl", "dispatch", "focuswindow", "address:" + address], check=True, stdout=subprocess.DEVNULL, timeout=3)
  elif action == "workspace" and len(sys.argv) == 3:
    value = sys.argv[2]
    if re.fullmatch(r"[1-9][0-9]{0,5}", value) and any(str(w["id"]) == value for w in query("workspaces")):
      subprocess.run(["hyprctl", "dispatch", "workspace", value], check=True, stdout=subprocess.DEVNULL, timeout=3)


if __name__ == "__main__":
  try:
    main()
  except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
    # Never leak compositor payloads or traceback paths into the persistent shell log.
    emit({"unavailable": True})
