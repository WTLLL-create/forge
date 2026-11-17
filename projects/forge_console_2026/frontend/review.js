/* Review workbench: trigger a review, poll status, render issues / patches /
 * verification / tool trace. All results come from the real API; nothing is
 * faked. The review never modifies the paper (plan.applied === false).
 *
 * This file depends on app.js only for the shared $ helper and the project /
 * runId selected there; it re-reads them from the DOM on every action so the
 * two files stay loosely coupled.
 */
(() => {
  const $ = (id) => document.getElementById(id);
  const state = { runId: null, timer: null };

  const fmtTime = (iso) =>
    iso ? new Date(iso).toLocaleString("zh-CN", { hour12: false }) : "—";

  const STATUS_TEXT = {
    none: "未运行",
    queued: "排队中",
    running: "审稿中",
    completed: "已完成",
    failed: "失败",
  };

  const STATUS_CLASS = {
    queued: "UNKNOWN",
    running: "RUNNING",
    completed: "PASS",
    failed: "FAIL",
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

  function currentRun() {
    return window.FORGE_STATE ? window.FORGE_STATE.runId : null;
  }

  function project() {
    const select = $("project-select");
    return select ? select.value : null;
  }

  function showError(message) {
    const box = $("review-error");
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function clearError() {
    $("review-error").classList.add("hidden");
  }

  function renderStatus(status) {
    const badge = $("review-status");
    const key = status.status || "none";
    badge.textContent = STATUS_TEXT[key] || key;
    badge.className = `status-badge ${STATUS_CLASS[key] || "UNKNOWN"}`;

    const meta = $("review-meta");
    if (key === "none") {
      meta.textContent = "";
      return;
    }
    const parts = [];
    if (status.planner) parts.push(`规划器：${status.planner === "rule" ? "规则（确定性）" : status.planner}`);
    if (status.steps != null) parts.push(`工具调用 ${status.steps} 步`);
    if (status.issues != null) parts.push(`问题 ${status.issues} 个`);
    if (status.patches != null) parts.push(`建议 ${status.patches} 条`);
    if (status.verdict) parts.push(`Verifier：${status.verdict}`);
    if (status.finished_at) parts.push(`完成于 ${fmtTime(status.finished_at)}`);
    meta.textContent = parts.join(" · ");
  }

  function renderIssues(issues) {
    const list = $("issue-list");
    list.innerHTML = "";
    $("issue-count").textContent = `（${issues.length}）`;

    if (!issues.length) {
      const row = document.createElement("div");
      row.className = "review-empty";
      row.textContent = "Reviewer 未发现问题（本轮为确定性规则检测）。";
      list.appendChild(row);
      return;
    }

    issues.forEach((issue) => {
      const card = document.createElement("div");
      card.className = "issue-card";

      const head = document.createElement("div");
      head.className = "issue-head";
      const sev = document.createElement("span");
      sev.className = `chip ${issue.severity === "high" ? "FAIL" : "UNKNOWN"}`;
      sev.textContent = issue.severity === "high" ? "HIGH" : "MEDIUM";
      const type = document.createElement("span");
      type.className = "issue-type";
      type.textContent = issue.type;
      const where = document.createElement("span");
      where.className = "mono small";
      const block = issue.evidence && issue.evidence.block_id ? `#${issue.evidence.block_id}` : "";
      where.textContent = `${issue.section || "—"}${block}`;
      head.append(sev, type, where);
      card.appendChild(head);

      const ev = document.createElement("div");
      ev.className = "issue-evidence mono";
      const evidence = issue.evidence || {};
      const text = evidence.claim || evidence.raw || evidence.gate || JSON.stringify(evidence);
      ev.textContent = String(text).slice(0, 160);
      card.appendChild(ev);

      const sg = document.createElement("div");
      sg.className = "issue-suggestion";
      sg.textContent = issue.suggestion || "";
      card.appendChild(sg);

      list.appendChild(card);
    });
  }

  function renderPatches(patches, applied) {
    const list = $("patch-list");
    list.innerHTML = "";
    $("patch-count").textContent = `（${patches.length}）`;

    const notice = document.createElement("div");
    notice.className = "review-notice";
    notice.textContent = applied
      ? "警告：计划标记为已应用。"
      : "以下均为建议，未回写论文原文（applied=false），需人工确认后才会被采纳。";
    list.appendChild(notice);

    if (!patches.length) {
      const row = document.createElement("div");
      row.className = "review-empty";
      row.textContent = "Writer 没有可生成的修订建议。";
      list.appendChild(row);
      return;
    }

    patches.forEach((patch) => {
      const card = document.createElement("div");
      card.className = "patch-card";

      const head = document.createElement("div");
      head.className = "issue-head";
      const id = document.createElement("span");
      id.className = "mono small";
      id.textContent = patch.patch_id;
      const where = document.createElement("span");
      where.className = "mono small";
      where.textContent = `${patch.section} #${patch.block_id}`;
      const action = document.createElement("span");
      action.className = "chip UNKNOWN";
      action.textContent = patch.action || "";
      const revised = document.createElement("span");
      if (patch.revised) {
        revised.className = "chip RUNNING";
        revised.textContent = "回退环修订";
      }
      head.append(id, action, where);
      if (patch.revised) head.appendChild(revised);
      card.appendChild(head);

      const oldP = document.createElement("div");
      oldP.className = "patch-line old";
      oldP.textContent = `- ${patch.old_claim || ""}`;
      const newP = document.createElement("div");
      newP.className = "patch-line new";
      newP.textContent = `+ ${patch.new_claim || ""}`;
      card.append(oldP, newP);

      const reason = document.createElement("div");
      reason.className = "issue-suggestion";
      reason.textContent = patch.reason || "";
      card.appendChild(reason);

      list.appendChild(card);
    });
  }

  function renderVerification(verification) {
    const badge = $("verdict-badge");
    const verdict = verification.verdict || "—";
    badge.textContent = verdict;
    badge.className = `status-badge ${verdict === "PASS" ? "PASS" : verdict === "EMPTY" ? "UNKNOWN" : "FAIL"}`;

    const list = $("verify-list");
    list.innerHTML = "";
    const results = verification.results || [];
    if (!results.length) {
      const row = document.createElement("div");
      row.className = "review-empty";
      row.textContent = "没有需要复核的补丁。";
      list.appendChild(row);
      return;
    }

    results.forEach((row) => {
      const card = document.createElement("div");
      card.className = "verify-card";

      const head = document.createElement("div");
      head.className = "issue-head";
      const id = document.createElement("span");
      id.className = "mono small";
      id.textContent = row.patch_id;
      const chip = document.createElement("span");
      chip.className = `chip ${row.status === "PASS" ? "PASS" : "FAIL"}`;
      chip.textContent = row.status;
      head.append(id, chip);
      card.appendChild(head);

      (row.checks || []).forEach((check) => {
        const line = document.createElement("div");
        line.className = "check-inline";
        const mark = document.createElement("span");
        mark.textContent = check.status === "PASS" ? "✓" : "✗";
        mark.className = check.status === "PASS" ? "ok-mark" : "bad-mark";
        const name = document.createElement("span");
        name.textContent = check.name;
        line.append(mark, name);
        card.appendChild(line);
      });

      list.appendChild(card);
    });
  }

  function renderTrace(trace) {
    $("trace-count").textContent = String(trace.length);
    const list = $("trace-list");
    list.innerHTML = "";
    trace.forEach((step) => {
      const row = document.createElement("div");
      row.className = "trace-row";
      const idx = document.createElement("span");
      idx.className = "idx";
      idx.textContent = String(step.step).padStart(2, "0");
      const tool = document.createElement("span");
      tool.className = "mono";
      tool.textContent = step.tool;
      const hash = document.createElement("span");
      hash.className = "mono muted small";
      hash.textContent = step.args_hash;
      const dur = document.createElement("span");
      dur.className = "dur";
      dur.textContent = `${step.elapsed_ms} ms`;
      row.append(idx, tool, hash, dur);
      list.appendChild(row);
    });
  }

  function renderResult(body) {
    const review = body.review;
    const plan = body.plan;
    $("review-result").classList.remove("hidden");

    if (!review || !plan) {
      $("issue-list").innerHTML = "";
      $("patch-list").innerHTML = "";
      $("verify-list").innerHTML = "";
      return;
    }

    renderIssues(review.issues || []);
    renderPatches(plan.patches || [], plan.applied);
    renderVerification(plan.verification || {});
    renderTrace(review.tool_trace || []);
  }

  async function loadReview() {
    const runId = currentRun();
    if (!runId) return;
    state.runId = runId;
    try {
      const body = await fetchJSON(
        `/api/runs/${encodeURIComponent(runId)}/review?project=${encodeURIComponent(project())}`
      );
      clearError();
      renderStatus(body.status || { status: "none" });
      if ((body.status || {}).status === "completed") {
        renderResult(body);
        stopPolling();
      } else if ((body.status || {}).status === "failed") {
        showError(`审稿失败：${body.status.error || "未知错误"}`);
        stopPolling();
      } else if ((body.status || {}).status === "running" || (body.status || {}).status === "queued") {
        startPolling();
      } else {
        $("review-result").classList.add("hidden");
      }
    } catch (error) {
      if (String(error.message).includes("unknown run")) return;
      showError(`读取审稿状态失败：${error.message}`);
    }
  }

  async function triggerReview() {
    const runId = currentRun();
    if (!runId) return;
    const button = $("review-button");
    button.disabled = true;
    clearError();
    try {
      const status = await fetchJSON(
        `/api/runs/${encodeURIComponent(runId)}/review?project=${encodeURIComponent(project())}`,
        { method: "POST" }
      );
      renderStatus(status);
      startPolling();
    } catch (error) {
      showError(`触发审稿失败：${error.message}`);
    } finally {
      button.disabled = false;
    }
  }

  function startPolling() {
    stopPolling();
    state.timer = setInterval(loadReview, 1500);
  }

  function stopPolling() {
    if (state.timer) {
      clearInterval(state.timer);
      state.timer = null;
    }
  }

  function bind() {
    $("review-button").addEventListener("click", triggerReview);
  }

  document.addEventListener("DOMContentLoaded", () => {
    bind();
    // Re-render whenever the run view is refreshed by app.js.
    const observer = new MutationObserver(() => {
      const runId = currentRun();
      if (runId && runId !== state.runId) loadReview();
    });
    const target = $("run-view");
    if (target) observer.observe(target, { attributes: true, attributeFilter: ["class"] });
  });

  window.FORGE_REVIEW = { loadReview };
})();
