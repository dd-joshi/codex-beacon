# Focus physical hero-path evidence — 20 August 2026

**Result:** Pass for the bounded one-minute path  
**Device:** authenticated `p6-c3-afb810`  
**Host:** first-party Peri6 Focus companion 0.1.0  
**Evidence source:** founder physical observation and screenshot supplied during the working session

## Procedure

1. Power the provisioned ESP/WS2812 prototype and connect the first-party
   companion over the private LAN.
2. Confirm the companion reports authenticated device ID `p6-c3-afb810`.
3. Set Focus duration to one minute and apply/reset it.
4. Start the timer and observe the six physical cells through completion and
   subsequent expiry/off behavior.

## Observed result

- Authentication succeeded against the expected device identity.
- Blue cells filled one by one across the one-minute countdown.
- All six cells became green when Focus reached successful completion.
- The completion indication subsequently cleared and the physical cells turned
  off.
- The companion UI and physical output agreed on the successful completion
  state.

This proves the bounded end-to-end path:

```text
Focus clock -> PackProposal -> host compiler -> authenticated LAN transport
            -> generic ESP renderer -> six physical cells -> safe off
```

No ESP application/Focus semantic or firmware change was required.

## Second-run transport observation

A subsequent physical run exposed a real desktop transport defect:

- `Fresh desired scene accepted` appeared about twice per second even though
  the six-cell visual had not changed;
- a device response exceeded the two-second response deadline;
- the companion lost the connection, retried, re-authenticated, and restored
  the current Focus state; and
- the cells were briefly off during recovery before returning to the running
  indication.

The code path and screenshots confirm redundant full `LOAD_SCENE` traffic and
the resulting stale-acknowledgment race. They do not, by themselves, prove the
ESP exceeded its raw processing capacity. The brief off interval is consistent
with the renderer's intentional three-second fail-safe lease expiring while the
desktop reconnected.

## Corrective action implemented; physical retest pending

The device manager now coalesces same-generation scenes whose complete
device-visible content is identical. A freshness-only Focus update extends the
exact host TTL without changing the transport stamp, so an in-flight
`LOAD_SCENE` or `KEEPALIVE` acknowledgment remains current. A real pixel,
brightness, playback, generation, expiry, or reconnect change still follows
the normal load/clear path.

Automated regressions prove that:

- refreshing an identical scene during a delayed load or keepalive produces
  one load and no stale transition;
- refreshed output remains alive beyond the original TTL using keepalives,
  without a second load or clear;
- a shorter refreshed TTL is honored, and republishing after a genuine expiry
  gap uses a new scene rather than resurrecting the old transport state;
- a changed visual and an identical visual in a new pack generation each cause
  a new load; and
- reconnect, expiry, stale-load rejection, and neutral-output behavior remain
  intact.

The full desktop suite is green: 77 tests ran, with one expected repository
metadata check skipped because this workspace copy has no `.git` directory.

The immediate physical check is a 10–15 minute Focus soak. During an unchanged
stage, the Activity panel should no longer show repeated scene-accepted lines.
Steady device traffic should be one small keepalive per second; full scene loads
should occur only at Start, each one-sixth progress boundary, a state change, or
a genuine reconnect. If another timeout occurs, preserve the complete ESP
serial log, especially reset reason, Wi-Fi events, and the one-minute heap/body
metrics line, before changing the firmware.

## What this does not yet prove

- physical pause, resume, reset, cancellation, unknown, or button-gesture paths;
- Windows sleep/wake, router restart, DHCP change, or long disconnect recovery;
- multi-hour connection/render soak behavior;
- the Blender journey or repeated pack switching;
- P1 parser fuzzing and measured stack/heap/timing exit evidence;
- power-system, enclosure, compliance, manufacturing, or sale readiness.

The broader P1/P2/P3 and software-prototype gates therefore remain open.