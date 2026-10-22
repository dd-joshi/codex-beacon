# PC companion UI surgical plan

**Decision date:** 21 August 2026  
**Status:** In progress; second founder-reviewed Focus visual iteration implemented

## Objective

Replace the prototype developer console with a compact Windows companion while
preserving the physically tested Focus pack, host, protocol, transport, and ESP
firmware.

This work does not require an ESP reflash. It changes presentation and desktop
interaction only.

## Frozen first-window direction

- Approximate window size: 720 x 360, with a landscape layout.
- Header: quiet `Peri6 Focus` pack-name menu, connection dot, Settings.
- Body: countdown, six small equally spaced LED pips, and restrained readable
  play/pause and stop controls.
- No endpoint, verbose state prose, interval labels, or activity log on the
  main surface.
- Endpoint, duration, connection controls, and diagnostics belong in Settings.
- The pack-name menu lists only installed and functional modes. Its `Add new…`
  action is the future registry entry point and must not imply that Weather,
  Render, or Ambient is installed before its pack exists.

Mode-specific meaning is data-driven. A future Weather mode permanently labels
the three equal two-cell groups and shows their current values:

```text
Temperature       Humidity       Rain chance
    31 C             64%             20%
   [1][2]           [3][4]          [5][6]
```

All six LED pips remain equally spaced; labels are centered over their pair.
The text is permanent so meaning never depends on colour or hover alone. These
labels are desktop-only pack-presentation metadata. They never enter the
generic DeviceScene or ESP protocol.

## Surgical implementation sequence

1. Separate connection, Focus-session, and renderer-output presentation state.
2. Derive countdown from structured progress rather than explanation prose.
3. Replace the Tkinter product console with the compact PySide6 window.
4. Reuse the active pack's recipe for the preview instead of duplicating pack
   colour constants in UI code.
5. Move configuration and diagnostics to Settings.
6. Verify DPI, keyboard access, reconnect behaviour, and the physical Focus
   hero path.
7. Add persistence, tray/background behaviour, reduced-motion settings, and
   standalone packaging after the first UI review.

## First review gate

- Pure reducer regressions pass, including stale output expiry.
- Existing desktop host, transport, protocol, and pack tests remain green.
- The Qt application starts and closes cleanly without a connected device.
- Founder reviews the compact visual direction before additional modes or
  packaging work begins.