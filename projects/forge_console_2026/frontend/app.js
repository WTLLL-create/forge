const state = {
  project: null,
  runId: null,
  run: null,
  logStage: null,
  logStream: "stdout",
  jobId: null,
  jobTimer: null,
};

/* Shared with review.js (loaded after this file). */
window.FORGE_STATE = state;

const $ = (id) => document.getElementById(id);

const fmtTime = (iso) =>
  iso ? new Date(iso).toLocaleString("zh-CN", { hour12: false }) : "—";

const fmtDur = (start, end) => {
  if (!start || !end) return "—";
  const ms = new Date(end) - new Date(start);
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} s`;
  return `${(ms / 60000).toFixed(1)} min`;
};

const fmtSize = (n) => {
  if (n == null) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
};

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return res.json();
}

function statusClass(status) {
  return ["PASS", "FAIL", "RUNNING"].includes(status) ? status : "UNKNOWN";
}

async function loadProjects() {
  const projects = await fetchJSON("/api/projects");
  const select = $("project-select");
  select.innerHTML = "";
  if (!projects.length) {
    const option = document.createElement("option");
    option.textContent = "没有可用项目";
    select.appendChild(option);
    return;
  }
  projects.forEach((project) => {
    const option = document.createElement("option");
    option.value = project.name;
    const stages = project.stage_count ? ` · ${project.stage_count} 阶段` : "";
    option.textContent = `${project.name}${stages}`;
    select.appendChild(option);
  });
  state.project = projects[0].name;
  select.value = state.project;
}

async function loadRuns() {
  const runs = await fetchJSON(`/api/runs?project=${encodeURIComponent(state.project)}`);
  const list = $("run-list");
  list.innerHTML = "";
  $("run-count").textContent = runs.length ? `${runs.length} 次` : "";
  $("run-empty").classList.toggle("hidden", runs.length > 0);

  runs.forEach((run) => {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.className = "run-item" + (run.run_id === state.runId ? " active" : "");
    button.dataset.runId = run.run_id;

    const line1 = document.createElement("span");
    line1.className = "run-line1";
    const dot = document.createElement("span");
    dot.className = `dot ${statusClass(run.status)}`;
    const name = document.createElement("span");
    name.textContent = run.run_id;
    line1.append(dot, name);

    const line2 = document.createElement("span");
    line2.className = "run-line2";
    const time = document.createElement("span");
    time.textContent = fmtTime(run.start_time);
    const progress = document.createElement("span");
    progress.textContent = `阶段 ${run.stages_pass}/${run.stages_total} · 门禁 ${run.gates_pass}/${run.gates_total}`;
    line2.append(time, progress);

    button.append(line1, line2);
    button.addEventListener("click", () => selectRun(run.run_id));
    li.appendChild(button);
    list.appendChild(li);
  });

  if (!state.runId && runs.length) {
    await selectRun(runs[0].run_id);
  }
}

async function selectRun(runId) {
  state.runId = runId;
  state.run = await fetchJSON(
    `/api/runs/${encodeURIComponent(runId)}?project=${encodeURIComponent(state.project)}`
  );
  document.querySelectorAll(".run-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.runId === runId);
  });
  renderRun();
  if (window.FORGE_REVIEW) await window.FORGE_REVIEW.loadReview();
}

function renderRun() {
  const run = state.run;
  if (!run) return;
  $("empty-state").classList.add("hidden");
  $("run-view").classList.remove("hidden");

  $("run-title").textContent = run.run_id;
  const total = run.stages?.length || 0;
  const passed = (run.stages || []).filter((s) => s.status === "PASS").length;
  $("run-meta").textContent = `${run.workflow_id || "—"} · ${fmtTime(run.start_time)} · 用时 ${fmtDur(
    run.start_time,
    run.end_time
  )}`;

  const badge = $("run-status");
  badge.textContent = run.status || "—";
  badge.className = `status-badge ${statusClass(run.status)}`;

  const gates = (run.gates || []).filter((g) => g.kind === "gate");
  const gatesPass = gates.filter((g) => g.status === "PASS").length;
  const artifacts = collectFiles(run.artifacts || []);

  const stats = [
    ["阶段通过", `${passed} / ${total}`],
    ["门禁通过", `${gatesPass} / ${gates.length}`],
    ["产物文件", `${artifacts.length}`],
    ["总耗时", fmtDur(run.start_time, run.end_time)],
  ];
  const grid = $("stat-grid");
  grid.innerHTML = "";
  stats.forEach(([label, value]) => {
    const card = document.createElement("div");
    card.className = "stat";
    const l = document.createElement("div");
    l.className = "label";
    l.textContent = label;
    const v = document.createElement("div");
    v.className = "value";
    v.textContent = value;
    card.append(l, v);
    grid.appendChild(card);
  });

  renderStages(run.stages || []);
  renderGates(run.gates || []);
  renderArtifacts(run.artifacts || []);
}

function renderStages(stages) {
  const list = $("stage-list");
  list.innerHTML = "";
  $("stage-count").textContent = `(${stages.length})`;

  stages.forEach((stage, index) => {
    const row = document.createElement("div");
    row.className = "stage-row";

    const idx = document.createElement("span");
    idx.className = "idx";
    idx.textContent = String(index + 1).padStart(2, "0");

    const name = document.createElement("span");
    name.className = "name";
    name.textContent = stage.stage;

    const chip = document.createElement("span");
    chip.className = `chip ${statusClass(stage.status)}`;
    chip.textContent = stage.status === "PASS" ? "PASS" : stage.status === "FAIL" ? "FAIL" : "—";

    const dur = document.createElement("span");
    dur.className = "dur";
    dur.textContent = fmtDur(stage.start_time, stage.end_time);

    const fresh = document.createElement("span");
    fresh.className = "fresh";
    fresh.textContent = stage.freshness_gate ? `新鲜度 ${stage.freshness_gate}` : "";

    row.append(idx, name, chip, dur, fresh);
    row.addEventListener("click", () => openLog(stage.stage));
    list.appendChild(row);
  });
}

function renderGates(gates) {
  const grid = $("gate-grid");
  const detail = $("gate-detail");
  grid.innerHTML = "";
  detail.classList.add("hidden");

  const main = gates.filter((g) => g.kind === "gate");
  const side = gates.filter((g) => g.kind !== "gate");
  const fragment = document.createDocumentFragment();

  main.forEach((gate) => {
    const card = document.createElement("button");
    card.className = "gate-card";
    card.type = "button";

    const name = document.createElement("div");
    name.className = "gate-name";
    name.textContent = gate.gate || gate.file;

    const meta = document.createElement("div");
    meta.className = "gate-meta";
    const checks = gate.checks || [];
    const passed = checks.filter((c) => c.status === "PASS").length;
    const left = document.createElement("span");
    left.textContent = `${passed}/${checks.length} checks`;
    const right = document.createElement("span");
    right.className = `chip ${statusClass(gate.status)}`;
    right.textContent = gate.status || "—";
    meta.append(left, right);

    card.append(name, meta);
    card.addEventListener("click", () => {
      grid.querySelectorAll(".gate-card").forEach((c) => c.classList.remove("active"));
      card.classList.add("active");
      renderGateDetail(gate);
    });
    fragment.appendChild(card);
  });

  grid.appendChild(fragment);

  if (side.length) {
    const note = document.createElement("p");
    note.className = "muted small";
    const bad = side.filter((g) => g.status && g.status !== "PASS");
    note.textContent = bad.length
      ? `另有 ${side.length} 份基础设施/新鲜度报告，其中 ${bad.length} 份非 PASS`
      : `另有 ${side.length} 份基础设施/新鲜度报告，均 PASS`;
    grid.appendChild(note);
  }
}

function renderGateDetail(gate) {
  const detail = $("gate-detail");
  detail.innerHTML = "";

  const head = document.createElement("div");
  head.className = "check-row head";
  ["状态", "检查项", "实际", "期望"].forEach((text) => {
    const cell = document.createElement("span");
    cell.textContent = text;
    head.appendChild(cell);
  });
  detail.appendChild(head);

  const checks = gate.checks || [];
  if (!checks.length) {
    const row = document.createElement("div");
    row.className = "check-row";
    row.textContent = "该报告没有逐项 checks。";
    detail.appendChild(row);
  }

  checks.forEach((check) => {
    const row = document.createElement("div");
    row.className = "check-row";

    const status = document.createElement("span");
    const chip = document.createElement("span");
    chip.className = `chip ${statusClass(check.status)}`;
    chip.textContent = check.status || "—";
    status.appendChild(chip);

    const name = document.createElement("span");
    name.textContent = check.name || "";

    const actual = document.createElement("span");
    actual.className = "mono";
    actual.textContent = JSON.stringify(check.actual ?? "");

    const expected = document.createElement("span");
    expected.className = "mono";
    expected.textContent = JSON.stringify(check.expected ?? "");

    row.append(status, name, actual, expected);
    detail.appendChild(row);
  });

  detail.classList.remove("hidden");
}

function collectFiles(tree, base = "") {
  const files = [];
  (tree || []).forEach((node) => {
    const path = base ? `${base}/${node.path}` : node.path;
    if (node.type === "dir") {
      files.push(...collectFiles(node.children || [], path));
    } else {
      files.push({ path, size: node.size });
    }
  });
  return files;
}

function renderArtifacts(tree) {
  const list = $("artifact-list");
  list.innerHTML = "";

  const walk = (nodes, depth) => {
    (nodes || []).forEach((node) => {
      const row = document.createElement("div");
      row.className = `artifact-row ${node.type === "dir" ? "dir" : "file"}`;

      const icon = document.createElement("span");
      icon.className = "icon";
      icon.textContent = node.type === "dir" ? "▾" : "·";

      const path = document.createElement("span");
      path.className = "path";
      path.textContent = node.path;

      const size = document.createElement("span");
      size.className = "size";
      size.textContent = node.type === "file" ? fmtSize(node.size) : "";

      row.append(icon, path, size);
      if (node.type === "file") {
        row.addEventListener("click", () => downloadArtifact(node.path));
      }
      list.appendChild(row);

      if (node.type === "dir" && depth < 2) {
        walk(node.children, depth + 1);
      }
    });
  };

  walk(tree, 0);
  if (!list.children.length) {
    const empty = document.createElement("div");
    empty.className = "artifact-row";
    empty.textContent = "这次运行没有登记产物。";
    list.appendChild(empty);
  }
}

function downloadArtifact(path) {
  const url = `/api/runs/${encodeURIComponent(state.runId)}/download?path=${encodeURIComponent(
    path
  )}&project=${encodeURIComponent(state.project)}`;
  window.location.href = url;
}

async function openLog(stage) {
  state.logStage = stage;
  state.logStream = "stdout";
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.stream === "stdout");
  });
  $("log-title").textContent = `${stage} · 日志`;
  $("log-modal").classList.remove("hidden");
  await loadLog();
}

async function loadLog() {
  const body = $("log-body");
  body.textContent = "加载中…";
  try {
    const url = `/api/runs/${encodeURIComponent(state.runId)}/logs/${encodeURIComponent(
      state.logStage
    )}/${state.logStream}?project=${encodeURIComponent(state.project)}`;
    const res = await fetch(url);
    const text = await res.text();
    body.textContent = text && text.trim() ? text : "（空）";
  } catch (error) {
    body.textContent = `读取失败：${error.message}`;
  }
}

function closeLog() {
  $("log-modal").classList.add("hidden");
}

async function startRun() {
  if (!state.project || state.jobId) return;
  const button = $("run-button");
  button.disabled = true;
  $("job-badge").classList.remove("hidden");
  $("job-badge").textContent = "排队中…";

  try {
    const job = await fetchJSON(`/api/jobs?project=${encodeURIComponent(state.project)}`, {
      method: "POST",
    });
    state.jobId = job.job_id;
    pollJob();
  } catch (error) {
    $("job-badge").textContent = `启动失败：${error.message}`;
    state.jobId = null;
    button.disabled = false;
  }
}

async function pollJob() {
  if (!state.jobId) return;
  try {
    const job = await fetchJSON(`/api/jobs/${state.jobId}`);
    if (job.status === "queued") {
      $("job-badge").textContent = "排队中…";
    } else if (job.status === "running") {
      $("job-badge").textContent = "运行中…";
    } else {
      $("job-badge").textContent =
        job.status === "ERROR" ? `失败：${job.message}` : `完成：${job.status}`;
      const runId = job.run_id;
      state.jobId = null;
      $("run-button").disabled = false;
      await loadRuns();
      if (runId) await selectRun(runId);
      return;
    }
  } catch (error) {
    $("job-badge").textContent = `轮询失败：${error.message}`;
    state.jobId = null;
    $("run-button").disabled = false;
    return;
  }
  state.jobTimer = setTimeout(pollJob, 1500);
}

function bindEvents() {
  $("project-select").addEventListener("change", async (event) => {
    state.project = event.target.value;
    state.runId = null;
    state.run = null;
    $("run-view").classList.add("hidden");
    $("empty-state").classList.remove("hidden");
    await loadRuns();
  });
  $("run-button").addEventListener("click", startRun);
  $("log-close").addEventListener("click", closeLog);
  $("log-modal").addEventListener("click", (event) => {
    if (event.target === $("log-modal")) closeLog();
  });
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", async () => {
      state.logStream = tab.dataset.stream;
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      await loadLog();
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeLog();
  });
}

async function init() {
  bindEvents();
  try {
    await loadProjects();
    await loadRuns();
  } catch (error) {
    $("run-empty").classList.remove("hidden");
    $("run-empty").textContent = `加载失败：${error.message}`;
  }
}

init();
