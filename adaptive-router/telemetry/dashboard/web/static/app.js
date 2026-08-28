const TARGETS = ["small_local", "large_local", "cloud"];
const PAGE_SIZE = 25;

const TARGET_LABELS = {
  small_local: "small_local",
  large_local: "large_local",
  cloud: "cloud",
};

let currentOffset = 0;
let currentFilter = "";
let totalDecisions = 0;
let currentRows = [];
let sortKey = "timestamp";
let sortDir = "desc";

function formatTime(ts) {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function formatUsd(value) {
  if (value == null) return "—";
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

function renderEmptyState() {
  document.getElementById("hero-section").innerHTML = `
    <div class="empty-state" style="grid-column: 1 / -1; border: none;">
      <h3>No routing data</h3>
      <p>
        Run requests through the router to populate
        <code>telemetry/routing.db</code>, then reload.
      </p>
    </div>
  `;
  document.getElementById("secondary-metrics").hidden = true;
  document.getElementById("target-chart").innerHTML =
    `<p class="loading">no data</p>`;
  document.getElementById("target-legend").innerHTML = "";
  document.getElementById("distribution-total").textContent = "";
}

function renderHero(data, decisions) {
  const cost = data.cost || {};
  const savingsPct = cost.savings_pct ?? 0;

  const total = decisions.length || data.total_requests || 0;
  const risky = decisions.filter(
    (row) => row.target === "small_local" && row.complexity_score >= 0.55
  ).length;
  const riskyPct = total ? (risky / total) * 100 : 0;

  document.getElementById("hero-section").innerHTML = `
    <div class="hero-primary">
      <p class="hero-value">${savingsPct.toFixed(1)}%</p>
      <p class="hero-label">api cost savings</p>
      <p class="hero-detail">
        <strong>${formatUsd(cost.savings_usd)}</strong> vs always-cloud ·
        <strong>${formatUsd(cost.per_1000_savings_usd)}</strong>/1k req
      </p>
    </div>
    <div class="hero-secondary">
      <p class="hero-value">${riskyPct.toFixed(1)}%</p>
      <p class="hero-label">high complexity → small_local</p>
      <p class="hero-detail">
        <strong>${risky}</strong> / <strong>${total}</strong> requests flagged
      </p>
    </div>
  `;
}

function renderSecondaryMetrics(data) {
  const byTarget = data.by_target || {};
  const container = document.getElementById("secondary-metrics");
  container.hidden = false;

  const cells = [
    {
      key: "total",
      label: "requests",
      value: data.total_requests ?? 0,
      sub: "logged",
    },
    ...TARGETS.map((target) => ({
      key: target,
      label: target,
      value: `${(byTarget[target]?.pct ?? 0).toFixed(1)}%`,
      sub: `${byTarget[target]?.count ?? 0} req · ${byTarget[target]?.avg_latency_ms ?? "—"} ms`,
    })),
  ];

  container.innerHTML = cells
    .map(
      (cell) => `
        <div class="stat-cell">
          <div class="cell-key">${escapeHtml(cell.label)}</div>
          <div class="cell-val">${escapeHtml(String(cell.value))}</div>
          <div class="cell-sub">${escapeHtml(cell.sub)}</div>
        </div>
      `
    )
    .join("");
}

function renderStackedBar(byTarget) {
  const chart = document.getElementById("target-chart");
  const total = TARGETS.reduce((sum, t) => sum + (byTarget[t]?.count ?? 0), 0);

  document.getElementById("distribution-total").textContent =
    total ? `n=${total}` : "";

  if (total === 0) {
    chart.innerHTML = `<p class="loading">no distribution data</p>`;
    return;
  }

  const segments = TARGETS.map((target) => {
    const count = byTarget[target]?.count ?? 0;
    if (!count) return "";
    const pct = (count / total) * 100;
    return `
      <div
        class="stacked-segment ${target}"
        style="width: ${pct}%"
        title="${target}: ${count} (${pct.toFixed(1)}%)"
      ></div>
    `;
  }).join("");

  const labels = TARGETS.map((target) => {
    const pct = byTarget[target]?.pct ?? 0;
    return `<span>${target} ${pct.toFixed(1)}%</span>`;
  }).join("");

  chart.innerHTML = `
    <div class="stacked-bar" role="img" aria-label="Horizontal stacked bar of routing targets">
      ${segments}
    </div>
    <div class="stacked-labels">${labels}</div>
  `;
}

function renderLegend(byTarget) {
  const legend = document.getElementById("target-legend");
  legend.innerHTML = TARGETS.map((target) => {
    const info = byTarget[target] || {};
    const pct = info.pct ?? 0;
    return `
      <div class="dist-row">
        <span class="dist-swatch ${target}" aria-hidden="true"></span>
        <span class="dist-name">${target}</span>
        <div class="dist-bar-inline">
          <div class="dist-bar-fill ${target}" style="width: ${Math.max(pct, pct > 0 ? 1 : 0)}%"></div>
        </div>
        <span class="dist-pct">${pct.toFixed(1)}%</span>
        <span class="dist-latency">${info.count ?? 0} · ${info.avg_latency_ms ?? "—"} ms</span>
      </div>
    `;
  }).join("");
}

function renderSummary(data, decisions) {
  if (!data.total_requests) {
    renderEmptyState();
    return;
  }

  renderHero(data, decisions);
  renderSecondaryMetrics(data);
  renderStackedBar(data.by_target || {});
  renderLegend(data.by_target || {});
}

async function fetchAllDecisions() {
  const all = [];
  let offset = 0;
  const limit = 200;
  while (true) {
    const data = await fetchJson(`/api/decisions?limit=${limit}&offset=${offset}`);
    all.push(...data.decisions);
    if (all.length >= data.total || !data.decisions.length) break;
    offset += limit;
  }
  return all;
}

function sortRows(rows) {
  const sorted = [...rows];
  sorted.sort((a, b) => {
    let av = a[sortKey];
    let bv = b[sortKey];
    if (sortKey === "timestamp" || sortKey === "latency_ms" || sortKey === "complexity_score") {
      av = Number(av);
      bv = Number(bv);
    }
    if (typeof av === "string") av = av.toLowerCase();
    if (typeof bv === "string") bv = bv.toLowerCase();
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });
  return sorted;
}

function renderTable(rows) {
  const tbody = document.getElementById("decisions-body");
  if (!rows.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="loading">no decisions match filter</td>
      </tr>
    `;
    return;
  }

  const sorted = sortRows(rows);
  tbody.innerHTML = sorted
    .map((row) => {
      const sensClass = row.sensitivity_flag ? "yes" : "no";
      const sensLabel = row.sensitivity_flag ? "yes" : "no";
      const complexity = row.complexity_score?.toFixed?.(3) ?? row.complexity_score ?? "—";
      return `
        <tr data-target="${escapeHtml(row.target)}">
          <td class="time">${escapeHtml(formatTime(row.timestamp))}</td>
          <td class="prompt">${escapeHtml(row.prompt)}</td>
          <td><span class="badge ${row.target}">${escapeHtml(row.target)}</span></td>
          <td class="reason">${escapeHtml(row.reason)}</td>
          <td class="num">${complexity}</td>
          <td><span class="badge ${sensClass}">${sensLabel}</span></td>
          <td class="num">${row.latency_ms}</td>
        </tr>
      `;
    })
    .join("");
}

function updatePagination() {
  const page = Math.floor(currentOffset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(totalDecisions / PAGE_SIZE));
  document.getElementById("page-info").textContent =
    `page ${page}/${totalPages} · ${totalDecisions} rows`;
  document.getElementById("prev-page").disabled = currentOffset === 0;
  document.getElementById("next-page").disabled =
    currentOffset + PAGE_SIZE >= totalDecisions;
}

async function loadDecisions() {
  const params = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String(currentOffset),
  });
  if (currentFilter) params.set("target", currentFilter);

  const data = await fetchJson(`/api/decisions?${params}`);
  totalDecisions = data.total;
  currentRows = data.decisions;
  renderTable(currentRows);
  updatePagination();
}

async function init() {
  try {
    const [summary, allDecisions] = await Promise.all([
      fetchJson("/api/summary"),
      fetchAllDecisions(),
    ]);
    renderSummary(summary, allDecisions);
    await loadDecisions();
  } catch (err) {
    document.getElementById("hero-section").innerHTML =
      `<p class="error">${escapeHtml(err.message)}</p>`;
    document.getElementById("decisions-body").innerHTML =
      `<tr><td colspan="7" class="error">${escapeHtml(err.message)}</td></tr>`;
  }
}

document.getElementById("target-filter").addEventListener("change", (e) => {
  currentFilter = e.target.value;
  currentOffset = 0;
  loadDecisions();
});

document.getElementById("prev-page").addEventListener("click", () => {
  currentOffset = Math.max(0, currentOffset - PAGE_SIZE);
  loadDecisions();
});

document.getElementById("next-page").addEventListener("click", () => {
  currentOffset += PAGE_SIZE;
  loadDecisions();
});

document.querySelectorAll("#decisions-table th[data-sort]").forEach((th) => {
  th.addEventListener("click", () => {
    const key = th.dataset.sort;
    if (sortKey === key) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortKey = key;
      sortDir = "asc";
    }
    renderTable(currentRows);
  });
});

init();
