# Codex Beacon — UI/UX handover (mobile page + PC companion)

> **Status (2026-10-28): superseded.** T1 and T2 were implemented; T3 was
> resolved via option (b) — `THINKING` shares the 2-hour long-task stale
> lease. The line numbers below describe the pre-fix state and are kept as
> the historical plan, not as current documentation.

Handed off: 2026-10-26.
Scope: fix the mobile status page layout, and redesign the PC companion window
to be readable at a glance from across a room. Nothing in this document has
been implemented yet — it is the exact-location plan for whoever picks this
up next (human or agent), written so each task can be done without re-deriving
the current layout from scratch.

## Read this first — how state reaches each surface

```
Codex hook --> AgentPack (packs/agent/pack.py)
            --> PresentationState (companion/presentation.py)   [PC window]
            --> StatusSnapshot    (companion/status.py)         [phone page]
            --> rendered by companion/app.py (PySide6)          [PC window]
               and companion/web/app.js + app.css (static page) [phone page]
```

Both surfaces consume the same semantic `state_key` (e.g. `agent.thinking`),
but each has its own, independently-styled rendering code. **Every visual fix
below touches only one surface's file(s)** — there is no shared stylesheet —
so when a change is meant to apply to both PC and phone, it has to be made in
both places by hand, matched by eye/value, same as `display.py`'s big comment
already warns ("Keep these values in step with the phone page's CSS
variables.").

## Already shipped this session (context only, not part of this handover)

`packs/agent/hook_sender.py`: added `BUILD_SCRIPT_PATTERN` / `TEST_SCRIPT_PATTERN`
so a wrapper script (e.g. `build_hil.ps1`, `run-tests.sh`) that doesn't
literally contain `pio run` / `cmake --build` / etc. still classifies as
`BUILDING`/`TESTING` and gets the long (2h) stale budget instead of the
generic `WORKING` 2-minute one. This fixed "Waiting for Codex" flashing
mid-build. Test: `tests/test_agent_hook_sender.py::test_wrapper_scripts_naming_build_or_test_are_classified`.
Full agent suite green: 21/21 (`tests/test_agent_*.py`).

---

## Problem inventory

### P1 — Mobile page: LEDs centered, status text reads bottom-left
File: `desktop/src/codex_beacon/companion/web/app.css`

- `.cells` is horizontally centered (`justify-content: center`, around line 194-199).
- `.status-card`'s children (`.pack`, `.headline`, `.detail`, `.meta`) are
  plain block elements with no `text-align`/`align-items` rule anywhere, so
  they default to left (around line 366-427).
- `.stage` is a *fixed* `flex: 0 0 40vh` band (line 178-191); `.status-card`
  is `flex: 1; justify-content: flex-start` (line 366-377) — i.e. the status
  text starts right after a large fixed LED band and is left-aligned, so on
  most phone screens it visually lands in the lower half of the screen,
  flush left, while the LEDs sit centered near the top-middle. That's the
  "LEDs in the middle, status bottom-left" you're seeing.

### P2 — PC companion window too small/quiet to read from across a room
File: `desktop/src/codex_beacon/companion/app.py`

- Window: `setMinimumSize(560, 290)`, `resize(680, 320)` (line 715-716) — small.
- Headline: the only status text is `self.timer` (`QLabel#Timer`), styled
  18pt normally and 30pt only in Focus-timer mode (`WINDOW_STYLE`, line
  160-167). Agent-mode headlines ("Waiting for Codex", "Ready for review", …)
  render at 18pt — smaller than the *phone* page's headline (`1.75rem`, i.e.
  ~24-28px, `app.css` line 387-399).
- LEDs: `LightStrip.paintEvent` hardcodes `diameter = 30.0`, `gap = 14.0`
  (`app.py` line 350-351) — smaller than the phone page's own `.cell`
  (`clamp(44px, 12vw, 48px)`, `app.css` line 201-204). The desk-bound,
  glance-from-distance surface currently has the *smaller* lights of the two
  — backwards from what it should be.
- No state-driven color wash: the phone page tints its whole background via
  `--state`/`--tint` per tone (`app.css` line 38-82). The PC window stays
  flat `#0f1115` regardless of state; color only shows up in the tiny LED
  dots, which is the first thing to get lost at distance.
- `state.detail` / `state.suggested_action` are populated
  (`presentation.py` line 100-101, 330-339) and already sent to the phone
  page, but **nothing in `app.py`'s `_render()` ever reads them** — the
  desktop window discards the one sentence of context ("A local tool is
  running.", "Approve or reply on your PC.") that would tell someone *what*
  is happening, not just that *something* is.

### P3 — THINKING-state false "Waiting for Codex" (known, open — needs a decision, see below)
Diagnosed earlier this session, not yet actioned. `STALE_ACTIVE_NS` = 2
minutes (`packs/agent/pack.py` line 40) also bounds the `THINKING` state, and
Codex emits no mid-reasoning heartbeat (only one `turn_started` at the start
of a turn). A genuinely long reasoning span — not just an unclassified tool
call — can still make the companion flash idle. The wrapper-script fix
shipped this session only closes the tool-call half of this; the bare-
reasoning half is still open.

---

## Fix plan — surgical tasks

### T1 — Center the mobile status block under the LEDs
File: `web/app.css`. No Python changes; no existing test covers CSS layout —
verify visually.

1. `.status-card` (line 366): add `align-items: center; text-align: center;`.
2. `.meta` (line 433): add `justify-content: center;` (it's already
   `display: flex; flex-wrap: wrap;`).
3. Replace the fixed 40dvh stage with a layout that centers the
   stage+status-card as *one* group instead of pinning the LEDs to a fixed
   top band:
   - `.app` (line 38): add `justify-content: center;` to its existing
     `display: flex; flex-direction: column;`.
   - `.stage` (line 178): change `flex: 0 0 40vh;` → `flex: 0 1 auto;
     padding: 2rem 0;` and drop the matching `@supports (height: 40dvh)`
     override (line 187-191) and the `min-width: 30rem` media override at
     line 508-510 that also sets a `dvh` basis.
   - `.controls` (line 447): add `margin-top: auto;` so Enable
     alerts/Mute stay pinned to the bottom instead of drifting toward the
     now-centered middle block.
4. Re-check the two existing breakpoints (`max-width: 30rem` line 502,
   `max-width: 340px` line 513) still look right once the stage is no longer
   height-locked — they currently only touch horizontal padding and cell
   size, should be unaffected, but confirm by eye.

Verification: open `index.html` in a phone-width responsive view (iPhone SE
through a large phone, both portrait heights) and confirm the headline/detail
sit horizontally centered directly beneath the LED row at every height, with
the alert buttons pinned to the bottom edge.

### T2 — Enlarge + add context to the PC companion window
File: `desktop/src/codex_beacon/companion/app.py`

1. **Window size** (line 715-716): `setMinimumSize(560, 290)` →
   `setMinimumSize(760, 420)`; `resize(680, 320)` → `resize(900, 480)`.
2. **LEDs** (`LightStrip`, line 314-426): `diameter = 30.0` → `48.0`,
   `gap = 14.0` → `20.0` (both inside `paintEvent`, line 350-351). Update
   `setMinimumSize(300, 64)` (line 321) and `sizeHint` (line 325-326, currently
   `QSize(380, 104 if self._groups else 64)`) proportionally so the widget
   doesn't clip the bigger circles — e.g. minimum `(420, 92)`, sizeHint
   `(520, 150 if self._groups else 92)`.
3. **Headline size**: reuse `self.timer` (don't add a second widget — Focus
   and Agent modes already share it via `main_text`). In `WINDOW_STYLE`:
   - `QLabel#Timer` base rule (line 160-164): `font-size: 18pt` → `26pt`.
   - `QLabel#Timer[timerMode="true"]` (line 165-167): `font-size: 30pt` →
     `36pt` (keeps the existing Focus/Agent size ratio rather than making
     them equal).
4. **Detail line**: add a new `QLabel` under `self.timer` in `_build()`
   (right after `content.addWidget(self.timer)`, line 842) — e.g.
   `self.detail_label`, `objectName("Detail")`, word-wrap on, centered,
   muted color (reuse `#9aa2b5`, same as `QToolButton#PrimaryAction`'s idle
   text color for consistency), hidden when empty. Add a matching
   `QLabel#Detail { ... }` rule to `WINDOW_STYLE`. Set its text in `_render()`
   near where `self.timer.setAccessibleName(...)` already reads
   `self.state.headline` (line 1190-1192):
   `self.detail_label.setText(self.state.detail)`,
   `self.detail_label.setVisible(bool(self.state.detail))`.
5. **State-tinted window background**: `companion.display` already exports
   `display_spec(state) -> DisplaySpec` with a `.tone` and the `TONE_COLORS`
   map (`display.py` line 53-60, 99-110) — reuse these directly so the PC
   window can never drift out of sync with the phone page's tone mapping.
   In `_render_lights()` (line 1251) or a small new `_render_tone()` called
   from `_render()`, compute `display_spec(self.state).tone`, map it through
   `TONE_COLORS`, and apply a subtle tinted background — prefer a thin
   colored bar/border on the central widget over recoloring the whole
   window background, to avoid fighting the existing `WINDOW_STYLE` QSS
   specificity and to keep this a glance cue, not a full repaint.

Verification:
- Launch: `../.venv/Scripts/codex-beacon.exe` (built entry point;
  `pyproject.toml` maps `codex-beacon = "codex_beacon.companion.app:main"`),
  or `PYTHONPATH=src ../.venv/Scripts/python.exe -m codex_beacon.companion.app`.
- Step through a few Agent states (idle/thinking/waiting/review) — either via
  the Agent hook test harness or by posting synthetic events at the Agent
  pack's listen port — and visually confirm size, headline, detail line, and
  tint all read correctly at arm's length and from a few meters away.
- Run the existing contract tests to make sure nothing in
  presentation/display broke (pure layout/QSS changes shouldn't, but these
  cover the state machine these widgets read from):
  `PYTHONPATH=src ../.venv/Scripts/python.exe -m unittest tests.test_companion_display tests.test_companion_presentation tests.test_agent_pack -v`
  (run from `desktop/`).

### T3 — Open decision: THINKING-state stale timeout (P3)
Do not implement until the user picks one — each has a real tradeoff:

- **(a) Raise `STALE_ACTIVE_NS` globally** (`packs/agent/pack.py` line 40,
  currently 2 minutes) to something like 5-8 minutes. Simplest change, one
  constant. Tradeoff: slower to notice a silently-cancelled turn (the
  original reason this constant is short — see the comment at line 37-39).
- **(b) Give `THINKING` the long `BUILDING`/`TESTING` budget**
  (`STALE_LONG_TASK_NS`, 2 hours) via `_stale_after_ns()` (line 324-331).
  Contradicts the existing comment's stated intent, so treat as a product
  decision, not a drive-by fix — needs explicit sign-off before touching.
- **(c) Add an intermediate "still going?" state** (amber, not grey) that
  the companion escalates to after the current short timeout, and only
  falls through to full `IDLE` after a second, longer timeout. Best UX,
  most code: a new `AgentState` member (`events.py`), a new recipe/
  explanation (`pack.py`), a new phone-page tone entry
  (`app.js`'s `stateTone` map + `app.css`), and new tests across
  `test_agent_pack.py` / `test_companion_display.py`.

---

## Files touched summary

| Task | Files |
|---|---|
| T1 | `desktop/src/codex_beacon/companion/web/app.css` |
| T2 | `desktop/src/codex_beacon/companion/app.py` |
| T3 (once decided) | `packs/agent/pack.py`, `packs/agent/events.py`, `companion/display.py`, `web/app.js`, `web/app.css`, plus tests |

## How to run the full agent/companion test suite
From `desktop/`:
```
PYTHONPATH=src ../.venv/Scripts/python.exe -m unittest discover -s tests -p "test_agent_*.py" -v
PYTHONPATH=src ../.venv/Scripts/python.exe -m unittest discover -s tests -p "test_companion_*.py" -v
```
(No `pytest` installed in `.venv` at handoff time — use stdlib `unittest`.)
