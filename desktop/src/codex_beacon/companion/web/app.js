(() => {
  "use strict";

  const app = document.getElementById("app");
  const phaseLabel = document.getElementById("phase");
  const packLabel = document.getElementById("pack");
  const headline = document.getElementById("headline");
  const detail = document.getElementById("detail");
  const action = document.getElementById("action");
  const cells = document.getElementById("cells");
  const age = document.getElementById("age");
  const updated = document.getElementById("updated");
  const offlineBanner = document.getElementById("offline");
  const alertsButton = document.getElementById("alerts");
  const muteButton = document.getElementById("mute");

  const pathMatch = location.pathname.match(/^\/s\/([^/]+)\//);
  const token = pathMatch ? decodeURIComponent(pathMatch[1]) : "";
  const transitionKey = token ? "codex-beacon.transition." + token : "";
  const lastAlertStateKey = token ? "codex-beacon.lastAlertState." + token : "";
  const lastAlertAtKey = token ? "codex-beacon.lastAlertAt." + token : "";
  const alertsKey = "codex-beacon.alerts";
  const mutedKey = "codex-beacon.muted";
  const offlineDefault = "Companion offline — showing last known status";

  const phaseText = {
    live: "Live",
    last_known: "Last known",
    stale: "Stale",
    offline: "Offline",
    error: "Error",
  };

  let latest = null;
  let receivedAt = 0;
  let baseAgeSeconds = null;
  let pollTimer = null;
  let failureCount = 0;
  let stopped = false;
  let offline = false;
  let audioContext = null;
  let soundUnavailable = false;
  let lastAlertAt = lastAlertAtKey
    ? Number(safeRead(lastAlertAtKey)) || 0
    : 0;
  let lastAlertState =
    (lastAlertStateKey && safeRead(lastAlertStateKey)) || "";
  let lastCellsSignature = "";
  let alertsEnabled = safeRead(alertsKey) === "1";
  let muted = safeRead(mutedKey) === "1";
  let lastTransition = transitionKey ? safeRead(transitionKey) || "" : "";

  function safeRead(key) {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function safeWrite(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      /* The page still works without storage. */
    }
  }

  function setText(element, value) {
    if (element.textContent !== value) {
      element.textContent = value;
    }
  }

  function setPhase(phase) {
    app.dataset.phase = phase;
    setText(phaseLabel, phaseText[phase] || "Connecting");
  }

  function setAlertsUi() {
    alertsButton.textContent = alertsEnabled
      ? soundUnavailable
        ? "Alerts on (vibrate)"
        : "Alerts on"
      : "Enable alerts";
    alertsButton.setAttribute("aria-pressed", String(alertsEnabled));
    muteButton.hidden = !alertsEnabled;
    muteButton.textContent = muted ? "Unmute" : "Mute";
    muteButton.setAttribute("aria-pressed", String(muted));
  }

  function renderCells(values) {
    const signature = JSON.stringify(Array.isArray(values) ? values.slice(0, 6) : []);
    if (signature === lastCellsSignature) {
      return;
    }
    lastCellsSignature = signature;
    while (cells.children.length < 6) {
      const dot = document.createElement("span");
      dot.className = "cell";
      cells.appendChild(dot);
    }
    for (let index = 0; index < 6; index += 1) {
      const dot = cells.children[index];
      const value = Array.isArray(values) ? values[index] : null;
      if (!Array.isArray(value) || value.length < 3) {
        dot.style.backgroundColor = "";
        dot.style.borderColor = "";
        dot.style.boxShadow = "";
        continue;
      }
      const red = clampColor(value[0]);
      const green = clampColor(value[1]);
      const blue = clampColor(value[2]);
      const active = red + green + blue > 36;
      dot.style.backgroundColor = active
        ? "rgb(" + red + ", " + green + ", " + blue + ")"
        : "";
      dot.style.borderColor = active ? "transparent" : "";
      dot.style.boxShadow = active
        ? "0 0 24px 6px rgba(" + red + ", " + green + ", " + blue + ", 0.6)"
        : "";
    }
  }

  function clampColor(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) {
      return 0;
    }
    return Math.max(0, Math.min(255, Math.round(number)));
  }

  function formatTime(value) {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return "";
    }
    return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function formatAge(seconds) {
    if (seconds < 5) {
      return "just now";
    }
    if (seconds < 60) {
      return Math.floor(seconds) + "s ago";
    }
    if (seconds < 3600) {
      return Math.floor(seconds / 60) + "m ago";
    }
    if (seconds < 86400) {
      return Math.floor(seconds / 3600) + "h ago";
    }
    return Math.floor(seconds / 86400) + "d ago";
  }

  function updateAge() {
    let seconds = null;
    if (baseAgeSeconds !== null) {
      seconds = Math.max(
        0,
        baseAgeSeconds + (Date.now() - receivedAt) / 1000
      );
    } else if (latest && latest.updated_at) {
      const timestamp = Date.parse(latest.updated_at);
      if (Number.isFinite(timestamp)) {
        seconds = Math.max(0, (Date.now() - timestamp) / 1000);
      }
    }
    if (seconds === null) {
      setText(age, "No update yet");
      return;
    }
    const prefix = offline ? "Last update " : "";
    setText(age, prefix + formatAge(seconds));
  }

  function render(data) {
    latest = data;
    receivedAt = Date.now();
    const reportedAge = data.age_seconds;
    baseAgeSeconds =
      typeof reportedAge === "number" && Number.isFinite(reportedAge)
        ? Math.max(0, reportedAge)
        : null;
    const phase = typeof data.phase === "string" ? data.phase : "error";
    offline = phase === "offline";
    app.dataset.attention =
      typeof data.attention === "string" ? data.attention : "normal";
    setPhase(phase);
    setText(packLabel, data.pack_name || "Codex Beacon");
    setText(headline, data.headline || "Waiting for status");
    setText(detail, data.detail || "");
    setText(action, data.suggested_action || "");
    action.hidden =
      !data.suggested_action ||
      phase === "stale" ||
      phase === "offline" ||
      phase === "error";
    renderCells(data.cells);
    offlineBanner.hidden = !offline;
    offlineBanner.textContent = offlineDefault;
    setText(
      updated,
      data.updated_at ? "Updated " + formatTime(data.updated_at) : ""
    );
    updateAge();
  }

  function showOffline() {
    offline = true;
    setPhase("offline");
    offlineBanner.hidden = false;
    action.hidden = true;
    if (!latest) {
      offlineBanner.textContent = "Companion offline — waiting for Codex Beacon on the PC";
      headline.textContent = "Waiting for companion";
      detail.textContent =
        "Start Codex Beacon on the PC and keep the phone on the same Wi-Fi.";
    }
    updateAge();
  }

  function showFatal(message) {
    stopped = true;
    offline = false;
    setPhase("error");
    headline.textContent = "Status page unavailable";
    detail.textContent = message;
    action.hidden = true;
    offlineBanner.hidden = true;
  }

  function ensureAudio() {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
      soundUnavailable = true;
      setAlertsUi();
      return false;
    }
    try {
      if (!audioContext) {
        audioContext = new AudioContextClass();
        soundUnavailable = false;
        setAlertsUi();
      }
      if (audioContext.state === "suspended") {
        audioContext.resume().catch(() => {});
      }
      return true;
    } catch (error) {
      audioContext = null;
      soundUnavailable = true;
      return false;
    }
  }

  function playChime(urgent) {
    if (!alertsEnabled || muted) {
      return;
    }
    if (typeof navigator.vibrate === "function") {
      try {
        navigator.vibrate(urgent ? [180, 80, 180] : [120]);
      } catch (error) {
        /* Vibration is best effort. */
      }
    }
    if (!ensureAudio()) {
      setAlertsUi();
      return;
    }
    try {
      const now = audioContext.currentTime + 0.02;
      const master = audioContext.createGain();
      master.gain.value = 0.7;
      master.connect(audioContext.destination);

      function tone(frequency, start, duration) {
        const oscillator = audioContext.createOscillator();
        const gain = audioContext.createGain();
        oscillator.type = "sine";
        oscillator.frequency.setValueAtTime(frequency, now + start);
        gain.gain.setValueAtTime(0.0001, now + start);
        gain.gain.exponentialRampToValueAtTime(0.22, now + start + 0.025);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + start + duration);
        oscillator.connect(gain);
        gain.connect(master);
        oscillator.start(now + start);
        oscillator.stop(now + start + duration + 0.03);
      }

      if (urgent) {
        tone(880, 0, 0.18);
        tone(660, 0.24, 0.3);
      } else {
        tone(760, 0, 0.32);
      }
    } catch (error) {
      /* Audio is best effort; never let it break status polling. */
    }
  }

  function maybeNotify(data) {
    const transition =
      typeof data.transition_id === "string" ? data.transition_id : "";
    if (!transition || transition === lastTransition) {
      return;
    }
    // Do not consume a transition seen only as stale. If the companion
    // recovers and the same state becomes live, it should still be eligible
    // for one alert.
    if (data.phase !== "live") {
      return;
    }
    lastTransition = transition;
    if (transitionKey) {
      safeWrite(transitionKey, transition);
    }
    if (
      alertsEnabled &&
      !muted &&
      data.notify &&
      data.notify !== "none"
    ) {
      const urgent = data.notify === "urgent";
      const terminal = ["agent.success", "agent.failure", "agent.review"];
      // A successful test/build or a failed check is often followed by
      // turn_stopped within seconds. Do not turn that one finish into two
      // chimes. An urgent waiting/input alert does not suppress the later
      // finish chime.
      const recentDuplicate =
        Date.now() - lastAlertAt < 30_000 &&
        terminal.indexOf(lastAlertState) !== -1 &&
        data.state_key === "agent.review";
      if (urgent || !recentDuplicate) {
        playChime(urgent);
        lastAlertAt = Date.now();
        lastAlertState = data.state_key || "";
        if (lastAlertAtKey) {
          safeWrite(lastAlertAtKey, String(lastAlertAt));
        }
        if (lastAlertStateKey) {
          safeWrite(lastAlertStateKey, lastAlertState);
        }
      }
    }
  }

  function schedule(milliseconds) {
    if (pollTimer !== null) {
      clearTimeout(pollTimer);
    }
    pollTimer = setTimeout(poll, milliseconds);
  }

  async function poll() {
    if (stopped) {
      return;
    }
    if (document.hidden) {
      schedule(2000);
      return;
    }

    let timeout = null;
    const controller =
      typeof AbortController === "function" ? new AbortController() : null;
    if (controller) {
      timeout = setTimeout(() => controller.abort(), 4000);
    }

    try {
      const response = await fetch("/api/status", {
        cache: "no-store",
        headers: { Authorization: "Bearer " + token },
        signal: controller ? controller.signal : undefined,
      });
      if (timeout !== null) {
        clearTimeout(timeout);
      }
      if (response.status === 401) {
        showFatal("This page link is no longer valid. Open the new URL from Codex Beacon.");
        return;
      }
      if (!response.ok) {
        throw new Error("HTTP " + response.status);
      }
      const data = await response.json();
      failureCount = 0;
      render(data);
      maybeNotify(data);
      schedule(1000);
    } catch (error) {
      if (timeout !== null) {
        clearTimeout(timeout);
      }
      failureCount += 1;
      if (failureCount >= 2) {
        showOffline();
      }
      schedule(failureCount >= 2 ? 2000 : 1000);
    }
  }

  alertsButton.addEventListener("click", () => {
    const audioAvailable = ensureAudio();
    const vibrationAvailable = typeof navigator.vibrate === "function";
    if (!audioAvailable && !vibrationAvailable) {
      alertsButton.textContent = "Alerts unavailable";
      alertsButton.disabled = true;
      return;
    }
    alertsEnabled = true;
    muted = false;
    safeWrite(alertsKey, "1");
    safeWrite(mutedKey, "0");
    setAlertsUi();
    if (audioAvailable) {
      playChime(false);
    } else {
      try {
        navigator.vibrate(60);
      } catch (error) {
        /* Vibration is best effort. */
      }
    }
  });

  muteButton.addEventListener("click", () => {
    muted = !muted;
    safeWrite(mutedKey, muted ? "1" : "0");
    setAlertsUi();
  });

  // Browsers can require a fresh user gesture after a reload before audio is
  // allowed. Arm the already-enabled alert sound on the next ordinary tap.
  document.addEventListener("click", () => {
    if (alertsEnabled && !muted && !ensureAudio()) {
      setAlertsUi();
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && !stopped) {
      schedule(0);
    }
  });

  window.addEventListener("pageshow", () => {
    if (!stopped) {
      schedule(0);
    }
  });

  setAlertsUi();
  setInterval(updateAge, 1000);

  if (!token) {
    showFatal("Use the phone URL shown in Codex Beacon settings.");
  } else {
    poll();
  }
})();
