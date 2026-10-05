# Privacy, review and verification

## What the plugin uses

The bridge reads current window addresses, app classes, rectangles, monitor/workspace identities, focus, groups, urgency and fullscreen/output state. It does not retain titles or application contents. Native screenshots in this repository render invented fixtures; they do not capture anyone's real application contents.

The watch loop listens for compositor events and coalesces bursts. Geometry checks run at most twice per second while active and eligible; idle polling is zero. The local visual state contains at most 32 random visual seeds and two booleans. Observed links and focus state live in memory and are reset on disconnection. Ambient surfaces are click-through; explicit app/workspace clicks validate a live target in both QML and Python before dispatch.

Structural roots are decorative geometry. Focus links represent observed focus changes; group links represent actual compositor groups. No link infers content exchange or a private semantic relationship. There is no Infomarchy feed, adapter or dependency.

## Reviewed decisions

The existing full Kimi K3 reviews were preserved locally; this repository carries their accepted decisions without private transcript/log records.

| Finding or design question | Result |
| --- | --- |
| Batched or fragmented stdin commands could stall in a buffered read | Bounded `os.read` draining handles complete lines, partial tails and EOF; event-loop regression test covers it. |
| Transient QML initialization could read unset coordinates | Snapshot guards and native cold-component creation checks cover it. |
| Actual 9px outer / 12px tiled gaps were smaller than the old routing offsets | Smaller gap-safe anchors and bounded knots/branches were verified with routing and pixel comparisons. |
| Hyprland maximized mode was mistaken for true fullscreen | Integer mode2 suppresses ambient; mode1 maximized retains eligible margins. Legacy boolean true remains supported. |
| Duplicate geometry frames cancelled a focus pulse | Unchanged frames preserve the current bounded pulse. |
| Overlapping Trace labels hid live app targets | Global finite pages replace collision-prone placement while preserving spatial cards when they fit. |
| Compact status text could overlap toolbar controls | Narrow status width and compact count/workspace text preserve readable controls. |
| Pager gaps or the page label could dismiss Trace | A bounded background hitbox absorbs those clicks; buttons retain their page actions. |
| Removing portal-reserved space could recover rows | Declined: it would overlap actual workspace controls. The compact fixture still fits down to320×360. |

No completed expensive full audit was repeated for the pagination change. Its focused correction review found no remaining correctness regression. Final fixture measurements tightened compact padding by 4px afterward; navigation logic was unchanged and final native tests used the resulting runtime hash.

## Verification matrix

Eight Python tests and the pure topology/tiled/resource suites pass. Native pointer tests enter every one of 48 app cards, check Previous/Next/page-label behavior, resize only the disposable fixture, preserve pages during same-workspace changes, clamp after removal, reject stale IDs and reset on workspace changes.

| Logical viewport | Scale | Cards per page | Pages for48 apps |
| --- | --- | --- | --- |
| 960×540 | 1× | 25 | 2 |
| 480×360 | 1× | 2 | 24 |
| 320×360 | 1× | 1 | 48 |
| 960×540 | 2× | 25 | 2 |

The existing native event/pulse/duplicate-frame, app/workspace, blank dismissal, overlap, stale-ID, move/close/urgency, outage and hidden/fullscreen/off/Still/Pause tests pass. Production Wayland types load in a hidden fixture. Geometry at logical widths960–2560 avoids app interiors; previous native tiled pixel comparisons found zero changed application-interior pixels.

The runtime baseline sourceTreeSHA256 is `500a79c63b665124c77e2b0cd246df597dcb5be3e184bc4f09a6b2f052293f10`. A live v3 activation on the development desktop is still pending. No v3 live resource benchmark is claimed: earlier samples were brief whole-fixture or bridge-only samples, not long-duration or incremental plugin-memory measurements.
