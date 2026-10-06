# Privacy, review and verification

## What the plugin uses

The bridge reads current window addresses, app classes, rectangles, the floating flag, monitor and workspace identities, the monitor's reserved edges (the bar) and open scratchpad, focus, groups, urgency and fullscreen or output state. It never retains titles or application contents. Native screenshots in this repository render invented fixtures; they do not capture anyone's real desktop.

The watch loop listens for compositor events and coalesces bursts. Geometry checks run at most twice per second while the user is active and an output is visible; idle polling is zero. Still mode keeps geometry checks on, because seams sit on window borders and must follow a resize even when nothing animates. The local visual state holds 32 random visual seeds and two booleans. Workspace hops, focus and pulse state live in memory and reset on disconnection. Ambient surfaces are click-through with no keyboard focus. Explicit window and workspace clicks validate a live target in both QML and Python before dispatch.

## Why v4 changed the design

v3 routed roots through empty space around windows. In real tiling layouts that space is 0 to 12 px, so on the development desktop (one window per workspace, 9 px outer margins) nothing visible was drawn, and Trace mapped only the current workspace. v4 draws on seams, which exist at every gap size, and maps every workspace. [REQUIREMENTS.md](REQUIREMENTS.md) lists the contract.

## Geometry rules

| Rule | How it is enforced |
| --- | --- |
| A side facing a neighbour sits at half the gap | `insets()`; neighbouring frames coincide exactly and merge into one seam |
| A side facing the screen edge sits mid-margin | Capped at 12 px; a margin under 1 px leaves the side open (not drawn) |
| Off-screen windows (scrolling layouts) | Fully off-screen windows are skipped; sides beyond the edge stay open |
| Overlapping tiled windows | The overlapped side stays open |
| Waviness and glow | Amplitude plus glow half-width plus line half-width never exceed the side's inset |
| Floating windows, overflow windows, scratchpad | Occluders: every root is cut exactly (Liang–Barsky) with room for its glow |
| Layout change or workspace switch | Seams hide immediately and regrow once geometry is stable for 450 ms |
| Motion budget | One urgent window pulses across all outputs; everything else moves only in response to an event |

## Independent review

A separate reviewer read the v4 runtime against these rules before release and reproduced its findings in node. Accepted and fixed:

| Finding | Result |
| --- | --- |
| Frames were clamped back onto the screen, putting lines inside windows that extend off-screen (scrolling layout) | Off-screen sides are open; fully off-screen windows are skipped; regression test with windows off both edges |
| A lone window with margins of 64 px or more got a zero inset | Each screen-facing side uses its own margin, capped at 12 px |
| A window flush with the screen edge got a line half on its content | Margins under 1 px leave the side open |
| Overlapping tiled windows treated the overlapped side as the screen edge | That side is open |
| The occluder cut ignored the glow width | The cut distance includes the glow half-width plus a spare pixel |
| Windows past the 24-window bound and an open scratchpad were neither framed nor occluding | Both are occluders now |
| Two outputs could each pulse an urgent window | One pulse, chosen across all outputs |
| A workspace switch drew seams while Hyprland slid windows in | Workspace and scratchpad changes count as layout changes |
| Trace could read a null controller during startup | Guarded |

Declined: recording hops only on same-monitor workspace switches. Moving focus to another monitor's workspace is a move between workspaces, so it stays a hop.

## Verification matrix

| Suite | What it proves |
| --- | --- |
| `tests/test_bridge.py`, `tests/test_watch.py` | Normalisation, privacy bounds, preferences, live-target validation, the real watch loop on a disposable compositor socket |
| `tests/test_topology.js` | Seams at 0, 1/2 and 9/12 px gaps, single window, floating occluder with glow, growth origin, spark paths, scrolling-layout and overlap regressions, scratchpad, 80-window stress, the Trace map and its pages |
| `tests/test_tiled.js` | 64 tiled layouts (960 to 2560 px wide, gaps 0/0, 1/2, 9/12, 21/22, one to five windows), plus the real status strings from `Service.qml` |
| `tests/test_resources.js` | The real QML geometry and render gates |
| `tests/isolated_native.py` | Production QML on a private X display: seams, focus growth, spark, settle, single pulse, layout regrow, gates, outage reset, Trace map, window and workspace clicks, backdrop dismissal, stale targets, and a **pixel audit** |
| `tests/native_pagination.py` | Every one of 24 workspaces reached through real pager clicks at 1920×1080, 960×540, 320×360 and 2× scale, with no binding loops |
| `tests/native_compile.py` | Production Wayland types load hidden in a real session |

The pixel audit renders each layout twice, with and without roots. It requires zero changed pixels inside every window and more than 1,500 changed seam pixels. Last run: 18,746 (9/12 gaps), 9,342 (zero gaps), 20,353 (one window) and 16,867 (floating window) changed pixels, all outside windows.

The runtime baseline is recorded in `tools/runtime-hashes.json`.
