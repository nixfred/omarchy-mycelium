# Mycelium v4 requirements

Each requirement has an ID. A commit names the IDs it touches. A requirement
counts as done only when it is visible and verified, not merely coded.

## Why v4 exists

v3 grew roots in the empty space between windows. Real tiling layouts barely
have any: a common setup leaves 9 px at the screen edge and 12 px between
windows, many people run zero gaps, and a single window per workspace leaves
only the outer margin. In those layouts v3 drew nothing a person could see.
Trace mapped only the current workspace, so a one-window workspace produced a
map with a single card.

## Ambient roots

| ID | Requirement |
| --- | --- |
| R1 | Roots follow **seams**, the lines where tiled windows meet each other and the screen edge. They render at gaps of 0, small gaps such as 9/12 px, and large gaps. A single window gets its own frame. |
| R2 | A seam root never covers application content. With a gap it stays inside the gap. With no gap it sits on the shared border line. |
| R3 | Floating windows add no seams, and no seam is drawn across a floating window. |
| R4 | Changing focus grows a root around the newly focused window, starting at the side nearest the previous window. Between non-adjacent windows, a spark first travels along the seams. All of this motion happens only in response to an event and stops within about a second. |
| R5 | An urgent window's seams turn amber. Only one element on screen pulses (the first urgent window); others stay static amber. The bar stem dot turns amber when any workspace has an urgent window. |
| R6 | After a layout change, seams hide and regrow once geometry is stable, so stale lines never linger over moved windows. |
| R7 | Organic waviness appears only where the gap leaves room for it. Zero-gap layouts get clean straight lines. |

## Trace map

| ID | Requirement |
| --- | --- |
| R8 | Trace shows **every** workspace as a scaled miniature of its monitor, holding that workspace's windows with app icon and name where they fit. The current workspace is highlighted, the focused window is accent-colored and urgent windows are amber. |
| R9 | Clicking a window jumps straight to it, on any workspace. Clicking a workspace switches to it. Done or the backdrop closes Trace. Targets are revalidated in QML and in the bridge. |
| R10 | Roots between workspace tiles show workspaces you actually moved between recently. They live only in memory, are bounded and are never written to disk. |
| R11 | Tiles never overlap the controls. When they do not fit, Trace pages instead of scrolling, down to a 320×360 logical output. |

## Kept guarantees

| ID | Requirement |
| --- | --- |
| R12 | Ambient surfaces stay click-through with no keyboard focus. Fullscreen, an off output, Pause, Still (no motion) and an unavailable connection behave as before. Idle polling stays at zero. No titles or application contents are read. All structures stay bounded. |
| R13 | The portable and native test suites cover v4 and pass, and CI is green. |
| R14 | v4 runs on the development desktop and is visible there. |
