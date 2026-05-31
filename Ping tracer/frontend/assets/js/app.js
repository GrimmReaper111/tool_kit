const MAX_TARGETS = 16;
const appState = {
  running: false,
  targets: [],
  latencyThreshold: 200,
  socket: null,
  cards: new Map(),
  chartRegistry: new Map(),
  anomalyHistory: [],
  sessionStore: new Map(),
  expandedTarget: null,
  expandedChart: null,
};

const dom = {
  startStopBtn: document.getElementById("start-stop-btn"),
  addTargetBtn: document.getElementById("add-target-btn"),
  clearAnomaliesBtn: document.getElementById("clear-anomalies-btn"),
  targetList: document.getElementById("target-list"),
  targetCount: document.getElementById("target-count"),
  cardsGrid: document.getElementById("cards-grid"),
  emptyState: document.getElementById("empty-state"),
  anomalyHistory: document.getElementById("anomaly-history"),
  latencyThreshold: document.getElementById("latency-threshold"),
  themeToggle: document.getElementById("theme-toggle"),
  expandedModal: document.getElementById("expanded-modal"),
  expandedTitle: document.getElementById("expanded-title"),
  expandedClose: document.getElementById("expanded-close"),
  expandedResetZoom: document.getElementById("expanded-reset-zoom"),
  expandedScroll: document.getElementById("expanded-chart-scroll"),
  expandedCanvas: document.getElementById("expanded-chart-canvas"),
};

function init() {
  renderTargetInputs(["8.8.8.8", "1.1.1.1"]);
  wireControls();
  syncThemeFromSystem();
  connectSocket();
  fetchState();
  renderAnomalyHistory();
}

function wireControls() {
  dom.addTargetBtn.addEventListener("click", () => {
    const values = readTargetsFromInputs();
    if (values.length >= MAX_TARGETS) return;
    values.push("");
    renderTargetInputs(values);
  });

  dom.startStopBtn.addEventListener("click", async () => {
    if (appState.running) {
      await stopMonitoring();
    } else {
      await startMonitoring();
    }
  });

  dom.clearAnomaliesBtn.addEventListener("click", () => {
    appState.anomalyHistory = [];
    renderAnomalyHistory();
  });

  dom.themeToggle.addEventListener("click", () => {
    const root = document.documentElement;
    root.classList.toggle("dark");
    localStorage.setItem("ping-tracer-theme", root.classList.contains("dark") ? "dark" : "light");
  });

  dom.expandedClose.addEventListener("click", closeExpandedChart);
  dom.expandedModal.addEventListener("click", (event) => {
    if (event.target === dom.expandedModal) {
      closeExpandedChart();
    }
  });

  dom.expandedResetZoom.addEventListener("click", () => {
    if (appState.expandedChart) {
      appState.expandedChart.resetZoom();
    }
  });
}

function syncThemeFromSystem() {
  const saved = localStorage.getItem("ping-tracer-theme");
  const root = document.documentElement;
  if (saved === "dark") root.classList.add("dark");
  if (saved === "light") root.classList.remove("dark");
}

function renderTargetInputs(values) {
  const normalized = values.slice(0, MAX_TARGETS);
  dom.targetList.innerHTML = "";

  normalized.forEach((value, idx) => {
    const row = document.createElement("div");
    row.className = "target-row";

    const input = document.createElement("input");
    input.className = "field-input";
    input.placeholder = `Target ${idx + 1}`;
    input.value = value;

    const removeBtn = document.createElement("button");
    removeBtn.className = "btn-secondary text-sm py-1.5 px-2.5";
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", () => {
      const current = readTargetsFromInputs();
      current.splice(idx, 1);
      renderTargetInputs(current.length ? current : [""]);
    });

    row.appendChild(input);
    row.appendChild(removeBtn);
    dom.targetList.appendChild(row);
  });

  if (!normalized.length) {
    renderTargetInputs([""]);
    return;
  }

  dom.targetCount.textContent = `${normalized.length} / ${MAX_TARGETS}`;
}

function readTargetsFromInputs() {
  return Array.from(dom.targetList.querySelectorAll("input"))
    .map((el) => el.value.trim())
    .filter((v) => v.length > 0)
    .slice(0, MAX_TARGETS);
}

async function fetchState() {
  const response = await fetch("/api/monitor/state");
  if (!response.ok) return;
  const data = await response.json();
  appState.running = data.running;
  appState.latencyThreshold = data.latency_threshold_ms;
  dom.latencyThreshold.value = String(data.latency_threshold_ms);
  if (Array.isArray(data.targets) && data.targets.length) {
    renderTargetInputs(data.targets);
  }
  updateStartStopButton();
}

async function startMonitoring() {
  const targets = readTargetsFromInputs();
  if (!targets.length) {
    alert("Please add at least one target.");
    return;
  }

  const threshold = Number(dom.latencyThreshold.value || 200);
  const payload = {
    targets,
    latency_threshold_ms: Number.isFinite(threshold) ? threshold : 200,
  };

  const response = await fetch("/api/monitor/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    alert("Unable to start monitoring.");
    return;
  }

  const state = await response.json();
  appState.running = state.running;
  appState.targets = state.targets;
  resetSessionData(state.targets);
  updateStartStopButton();
  ensureCards(state.targets);
}

async function stopMonitoring() {
  const response = await fetch("/api/monitor/stop", { method: "POST" });
  if (!response.ok) {
    alert("Unable to stop monitoring.");
    return;
  }

  appState.running = false;
  updateStartStopButton();
}

function updateStartStopButton() {
  dom.startStopBtn.textContent = appState.running ? "Stop Monitoring" : "Start Monitoring";
  dom.startStopBtn.classList.toggle("opacity-90", appState.running);
}

function connectSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws`);
  appState.socket = socket;

  socket.addEventListener("open", () => {
    setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send("ping");
    }, 15000);
  });

  socket.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    handleSocketEvent(msg);
  });

  socket.addEventListener("close", () => {
    setTimeout(connectSocket, 1200);
  });
}

function handleSocketEvent(event) {
  if (event.type === "monitoring_state") {
    appState.running = !!event.data.running;
    appState.targets = event.data.targets || [];
    updateStartStopButton();
    if (appState.targets.length) {
      renderTargetInputs(appState.targets);
      ensureCards(appState.targets);
    }
    return;
  }

  if (event.type === "device_update") {
    persistSessionSample(event.data);
    upsertDeviceCard(event.data);
    if (appState.expandedTarget === event.data.target) {
      renderExpandedChart(event.data.target);
    }
    return;
  }

  if (event.type === "anomaly") {
    persistSessionAnomaly(event.data);
    appState.anomalyHistory.unshift(event.data);
    appState.anomalyHistory = appState.anomalyHistory.slice(0, 500);
    renderAnomalyHistory();
    if (appState.expandedTarget === event.data.target) {
      renderExpandedChart(event.data.target);
    }
  }
}

function ensureCards(targets) {
  const active = new Set(targets);
  appState.cards.forEach((_value, target) => {
    if (!active.has(target)) {
      const card = appState.cards.get(target);
      const chart = appState.chartRegistry.get(target);
      if (chart) chart.destroy();
      if (card) card.remove();
      appState.cards.delete(target);
      appState.chartRegistry.delete(target);
    }
  });

  targets.forEach((target) => {
    initializeSessionTarget(target);
    if (!appState.cards.has(target)) {
      const card = createDeviceCard(target);
      appState.cards.set(target, card);
      dom.cardsGrid.appendChild(card);
    }
  });

  dom.emptyState.classList.toggle("hidden", targets.length > 0);
}

function createDeviceCard(target) {
  const card = document.createElement("article");
  card.className = "device-card status-healthy animate-fade-in-up";
  card.dataset.target = target;
  card.innerHTML = `
    <div class="flex items-center justify-between gap-2 mb-2">
      <h3 class="font-display text-base font-semibold break-all">${escapeHtml(target)}</h3>
      <div class="flex items-center gap-2">
        <span class="status-pill status-healthy" data-role="status-pill">Healthy</span>
        <button class="btn-secondary text-xs py-1 px-2" data-role="expand-btn">Expand</button>
      </div>
    </div>
    <div class="text-xs text-slate-600 dark:text-slate-300 mb-2" data-role="meta">Waiting for samples...</div>
    <div class="h-44"><canvas></canvas></div>
    <div class="mt-2 text-xs text-slate-600 dark:text-slate-300" data-role="reason"></div>
  `;

  const expandBtn = card.querySelector('[data-role="expand-btn"]');
  expandBtn.addEventListener("click", () => openExpandedChart(target));

  const chart = new Chart(card.querySelector("canvas").getContext("2d"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Latency (ms)",
          data: [],
          borderColor: "#0ea5e9",
          backgroundColor: "rgba(14, 165, 233, 0.15)",
          yAxisID: "y",
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.3,
        },
        {
          label: "Packet Loss (%)",
          data: [],
          borderColor: "#f59e0b",
          backgroundColor: "rgba(245, 158, 11, 0.15)",
          yAxisID: "y1",
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.2,
        },
        {
          label: "Anomaly Marker",
          data: [],
          borderColor: "#ef4444",
          backgroundColor: "#ef4444",
          yAxisID: "y",
          showLine: false,
          pointStyle: "triangle",
          pointRadius: 4,
          pointHoverRadius: 5,
        },
      ],
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { ticks: { display: false }, grid: { display: false } },
        y: {
          beginAtZero: true,
          title: { display: true, text: "Latency" },
          grid: { color: "rgba(148, 163, 184, 0.2)" },
        },
        y1: {
          beginAtZero: true,
          max: 100,
          position: "right",
          title: { display: true, text: "Loss %" },
          grid: { drawOnChartArea: false },
        },
      },
      plugins: {
        legend: { labels: { boxWidth: 10 } },
      },
    },
  });

  appState.chartRegistry.set(target, chart);
  return card;
}

function upsertDeviceCard(data) {
  const target = data.target;
  if (!appState.cards.has(target)) {
    ensureCards([...appState.targets, target]);
  }

  const card = appState.cards.get(target);
  const chart = appState.chartRegistry.get(target);
  if (!card || !chart) return;

  const labels = data.history.map((p) => formatTime(p.timestamp));
  const latencyValues = data.history.map((p) => (p.success ? p.latency_ms : null));

  const packetLossSeries = [];
  let failures = 0;
  data.history.forEach((p, idx) => {
    if (!p.success) failures += 1;
    packetLossSeries.push(Number(((failures / (idx + 1)) * 100).toFixed(2)));
  });

  const markerSet = getAnomalyMarkerSetForWindow(target, data.history);
  const anomalyMarkers = data.history.map((p, idx) => {
    if (!markerSet.has(idx)) return null;
    return p.success ? p.latency_ms : 0;
  });

  chart.data.labels = labels;
  chart.data.datasets[0].data = latencyValues;
  chart.data.datasets[1].data = packetLossSeries;
  chart.data.datasets[2].data = anomalyMarkers;
  chart.update("none");

  const statusMap = {
    healthy: { label: "Healthy", cls: "status-healthy" },
    warning: { label: "High Latency", cls: "status-warning" },
    critical: { label: "Down / Packet Loss", cls: "status-critical" },
  };

  const status = statusMap[data.status] || statusMap.healthy;
  card.classList.remove("status-healthy", "status-warning", "status-critical");
  card.classList.add(status.cls);

  const pill = card.querySelector('[data-role="status-pill"]');
  pill.textContent = status.label;
  pill.classList.remove("status-healthy", "status-warning", "status-critical");
  pill.classList.add(status.cls);

  const latestLatency = data.latency_ms === null ? "timeout" : `${data.latency_ms.toFixed(1)}ms`;
  const meta = card.querySelector('[data-role="meta"]');
  meta.textContent = `Latency: ${latestLatency} | Loss: ${data.packet_loss_pct}% | Session samples: ${getSessionSamples(target).length}`;

  const reason = card.querySelector('[data-role="reason"]');
  reason.textContent = data.anomaly_reasons?.length ? data.anomaly_reasons.join(" | ") : "No active anomalies";
}

function openExpandedChart(target) {
  appState.expandedTarget = target;
  dom.expandedTitle.textContent = `Expanded Trace - ${target}`;
  dom.expandedModal.classList.remove("hidden");
  renderExpandedChart(target);
}

function closeExpandedChart() {
  dom.expandedModal.classList.add("hidden");
  appState.expandedTarget = null;
  if (appState.expandedChart) {
    appState.expandedChart.destroy();
    appState.expandedChart = null;
  }
}

function renderExpandedChart(target) {
  const session = appState.sessionStore.get(target);
  if (!session) return;

  const samples = session.samples;
  const labels = samples.map((s) => formatTime(s.timestamp));
  const latency = samples.map((s) => (s.success ? s.latency_ms : null));
  const packetLoss = samples.map((s) => s.packet_loss_pct);

  const markerMap = new Set(session.anomalies.map((item) => timestampKey(item.timestamp)));
  const anomalyData = samples.map((sample) => {
    if (!markerMap.has(timestampKey(sample.timestamp))) return null;
    return sample.success ? sample.latency_ms : 0;
  });

  const minCanvasWidth = Math.max(920, labels.length * 22);
  dom.expandedCanvas.width = minCanvasWidth;
  dom.expandedCanvas.height = 760;

  if (appState.expandedChart) {
    appState.expandedChart.destroy();
  }

  appState.expandedChart = new Chart(dom.expandedCanvas.getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Latency (ms)",
          data: latency,
          borderColor: "#0ea5e9",
          backgroundColor: "rgba(14, 165, 233, 0.1)",
          yAxisID: "y",
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 4,
          tension: 0.22,
        },
        {
          label: "Packet Loss (%)",
          data: packetLoss,
          borderColor: "#f59e0b",
          backgroundColor: "rgba(245, 158, 11, 0.15)",
          yAxisID: "y1",
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 4,
          tension: 0.2,
        },
        {
          label: "Anomaly Marker",
          data: anomalyData,
          borderColor: "#ef4444",
          backgroundColor: "#ef4444",
          yAxisID: "y",
          showLine: false,
          pointStyle: "triangle",
          pointRadius: 5,
          pointHoverRadius: 7,
        },
      ],
    },
    options: {
      animation: false,
      responsive: false,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: {
          ticks: {
            autoSkip: true,
            maxTicksLimit: 24,
          },
          grid: { color: "rgba(148, 163, 184, 0.18)" },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: "Latency (ms)" },
          grid: { color: "rgba(148, 163, 184, 0.2)" },
        },
        y1: {
          beginAtZero: true,
          max: 100,
          position: "right",
          title: { display: true, text: "Packet Loss %" },
          grid: { drawOnChartArea: false },
        },
      },
      plugins: {
        legend: { position: "top" },
        zoom: {
          pan: {
            enabled: true,
            mode: "xy",
          },
          zoom: {
            wheel: {
              enabled: true,
            },
            pinch: {
              enabled: true,
            },
            mode: "xy",
          },
        },
      },
    },
  });
}

function renderAnomalyHistory() {
  dom.anomalyHistory.innerHTML = "";
  if (!appState.anomalyHistory.length) {
    const empty = document.createElement("p");
    empty.className = "text-sm text-slate-600 dark:text-slate-300";
    empty.textContent = "No anomalies logged yet.";
    dom.anomalyHistory.appendChild(empty);
    return;
  }

  appState.anomalyHistory.forEach((entry) => {
    const dt = new Date(entry.timestamp * 1000).toLocaleTimeString();
    const item = document.createElement("div");
    item.className = `anomaly-item severity-${entry.severity}`;
    item.innerHTML = `
      <div class="text-xs font-semibold uppercase tracking-wide">${escapeHtml(entry.severity)}</div>
      <div class="text-sm font-semibold">${escapeHtml(entry.target)}</div>
      <div class="text-sm">${escapeHtml(entry.message)}</div>
      <div class="text-xs text-slate-500 dark:text-slate-400">${dt}</div>
    `;
    dom.anomalyHistory.appendChild(item);
  });
}

function resetSessionData(targets) {
  appState.sessionStore.clear();
  appState.anomalyHistory = [];
  renderAnomalyHistory();

  targets.forEach((target) => {
    initializeSessionTarget(target);
  });
}

function initializeSessionTarget(target) {
  if (appState.sessionStore.has(target)) return;

  appState.sessionStore.set(target, {
    samples: [],
    anomalies: [],
  });
}

function persistSessionSample(data) {
  initializeSessionTarget(data.target);
  const targetState = appState.sessionStore.get(data.target);
  const samples = targetState.samples;
  const last = samples[samples.length - 1];

  const sample = {
    timestamp: data.timestamp,
    latency_ms: data.latency_ms,
    success: data.latency_ms !== null,
    packet_loss_pct: Number(data.packet_loss_pct),
    status: data.status,
  };

  if (!last || sample.timestamp > last.timestamp) {
    samples.push(sample);
  } else if (sample.timestamp === last.timestamp) {
    samples[samples.length - 1] = sample;
  }
}

function persistSessionAnomaly(anomaly) {
  initializeSessionTarget(anomaly.target);
  const targetState = appState.sessionStore.get(anomaly.target);

  const already = targetState.anomalies.some(
    (item) =>
      timestampKey(item.timestamp) === timestampKey(anomaly.timestamp) &&
      item.alert_type === anomaly.alert_type
  );

  if (!already) {
    targetState.anomalies.push(anomaly);
  }
}

function getSessionSamples(target) {
  return appState.sessionStore.get(target)?.samples ?? [];
}

function getAnomalyMarkerSetForWindow(target, windowHistory) {
  const output = new Set();
  const anomalies = appState.sessionStore.get(target)?.anomalies ?? [];

  windowHistory.forEach((point, idx) => {
    const matching = anomalies.some((anomaly) => Math.abs(anomaly.timestamp - point.timestamp) < 0.6);
    if (matching) {
      output.add(idx);
    }
  });

  return output;
}

function timestampKey(timestamp) {
  return Number(timestamp).toFixed(3);
}

function formatTime(timestamp) {
  return new Date(timestamp * 1000).toLocaleTimeString();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

init();
