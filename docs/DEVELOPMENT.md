# Development

Python 3.10+ and Node.js 18+ are sufficient for the portable bridge, topology and gate tests. The runtime needs an existing Omarchy Quattro/Hyprland desktop with Quickshell and Python 3.

```bash
python3 tools/verify-runtime.py
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_topology.js
node tests/test_tiled.js
node tests/test_resources.js
```

The eight Python tests cover metadata normalization, bounds/privacy, preferences, live-ID validation and the real watch loop against a disposable compositor socket. Node checks exercise geometry routing, grouping, portals, tiled gaps, statuses and the actual QML resource predicates. CI runs these checks and the project link/asset/privacy check.

## Native fixtures

Native tests additionally need `qs`, QtTest, Xvfb, the required Qt XCB backend and Omarchy's shell imports. Existing installations are discovered through `OMARCHY_PATH`, the `omarchy` executable or the standard `/usr/share/omarchy` location. Set `OMARCHY_PATH` explicitly for a source checkout.

```bash
python3 tests/isolated_native.py
MYCELIUM_TEST_SIZE=960x540 python3 tests/native_pagination.py
MYCELIUM_TEST_SIZE=320x360 python3 tests/native_pagination.py
MYCELIUM_TEST_SIZE=1920x1080 QT_SCALE_FACTOR=2 python3 tests/native_pagination.py
```

The fixtures allocate private X displays automatically. They strip only Wayland layer-shell attached properties in disposable copies, leaving production QML items, shapes and controls intact. Synthetic geometry and app metadata are used for captures. No real application content, user focus or live shell configuration is accessed by these fixtures. Output goes to ignored `local-evidence/`.

For the real Wayland-type check, run from your existing Wayland session:

```bash
python3 tests/native_compile.py
```

All fixture surfaces stay hidden in that check. `XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY` come from your session. A successful load checks actual production types without opening Trace or moving focus.

## Runtime layout

`bridge.py` normalizes compositor metadata, validates explicit navigation again, and exposes an event-driven watch stream. `v3/Service.qml` owns current geometry and ephemeral observed links. `v3/Topology.js` routes bounded roots around actual rectangles. `v3/Network.qml` draws the network. `v3/Trace.qml` supplies explicit app/workspace controls, and `v3/Widget.qml` supplies the bar stem.

The hash file describes the tested runtime baseline, not every source-project file. Runtime edits should update that baseline only after review and verification. Preserve versioned QML entry points when a fresh component URL is needed in the shared shell engine; the repository does not change global caches or restart the shell automatically.
