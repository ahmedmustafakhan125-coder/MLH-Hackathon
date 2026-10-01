"use strict";
// Squeeze dashboard client. No framework, no external requests. All model/task text goes through
// textContent and is never parsed as HTML, so model output can't inject markup.
(() => {
  const DEMO = "Write a Python function validate_email(s) that returns True or False, with pytest tests and short usage docs.";
  const SPIN = "|/-\\";
  const $ = (id) => document.getElementById(id);
  const S = { run: null, next: 0, timer: 0, spinTimer: 0, spinI: 0, stack: [], plan: new Map(), started: 0, ready: false };

  function h(tag, cls, ...kids) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    for (const k of kids.flat()) if (k != null && k !== false) el.append(k instanceof Node ? k : String(k));
    return el;
  }
  const n1 = (v) => (v == null || isNaN(v) ? "-" : Number(v).toFixed(1));
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (_) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (_) { /* private window */ } },
  };

  async function api(path, opts) {
    const res = await fetch(path, Object.assign({ cache: "no-store" }, opts));
    let data = {};
    try { data = await res.json(); } catch (_) { /* empty body */ }
    if (!res.ok) { const e = new Error(data.error || "HTTP " + res.status); e.status = res.status; throw e; }
    return data;
  }

  // ---------------- system state ----------------
  function setText(id, v) { const el = $(id); if (el) el.textContent = v; }

  function renderState(s) {
    S.ready = s.ready;
    const live = s.live, prof = s.profile;
    setText("st-os", live.os);
    setText("st-os-s", live.machine);
    setText("st-cpu", `${live.cpu_physical} / ${live.cpu_logical}`);
    setText("st-ram", `${n1(live.ram_available_gb)} GB`);
    setText("st-ram-s", `of ${n1(live.ram_total_gb)} GB total`);
    $("st-ram-bar").style.width = `${Math.max(0, Math.min(100, 100 * (1 - live.ram_available_gb / live.ram_total_gb)))}%`;
    setText("st-gpu", prof ? (prof.gpu ? prof.gpu.name : "None") : "-");
    setText("st-gpu-s", prof ? (prof.gpu ? `${prof.gpu.vram_free_gb} GB VRAM free` : "iGPU shares system RAM") : "run setup");
    setText("st-backend", prof ? String(prof.backend).toUpperCase() : "-");
    setText("st-co", s.ready ? (s.co_resident ? "both models fit together" : "models swap in and out") : "not profiled");
    $("setup-callout").hidden = s.ready;
    for (const role of ["heavy", "tiny"]) renderModel(role, s.models && s.models[role], s.tuning && s.tuning[role]);

    const p = s.privacy;
    setText("led-blocked", p.blocked);
    const guard = $("led-guard");
    guard.textContent = p.enabled ? "ACTIVE" : "STANDBY";
    guard.classList.toggle("ledger__num--on", p.enabled);
    setText("sys-version", `V. ${s.version}`);
    setText("foot-version", `v${s.version}`);
    renderTerm(s);
    if (!isRunning()) $("run-btn").disabled = !s.ready;
  }

  function renderModel(role, m, tuning) {
    const card = $(`m-${role}`);
    const f = (name) => card.querySelector(`[data-f="${name}"]`);
    f("name").textContent = m ? m.name : "Not tuned";
    f("placement").textContent = m ? `${m.placement} · ${m.key}` : "run setup to tune";
    f("threads").textContent = m ? m.threads : "-";
    f("tok_s").textContent = m ? n1(m.tok_s) : "-";
    f("ram_gb").textContent = m ? `${n1(m.ram_gb)} GB` : "-";
    f("ctx").textContent = m ? Number(m.ctx).toLocaleString("en-US") : "-";
    const bars = f("tuning");
    bars.replaceChildren();
    if (!tuning || !tuning.length) return;
    const max = Math.max(...tuning.map((r) => r.tok_s || 0), 1);
    bars.append(h("div", "bars__t", "TUNING · TOK/S BY THREAD COUNT"));
    for (const r of tuning) {
      const best = m && r.ok && r.threads === m.threads && r.ngl === m.ngl;
      const fill = h("i", "bar__fill");
      fill.style.width = `${(100 * (r.tok_s || 0)) / max}%`;
      bars.append(h("div", "bar" + (best ? " bar--best" : "") + (r.ok ? "" : " bar--fail"),
        h("span", null, `${r.threads} thr`), h("span", "bar__track", fill),
        h("span", null, r.ok ? `${n1(r.tok_s)}${best ? " ←" : ""}` : "failed")));
    }
  }

  function renderTerm(s) {
    const m = s.models || {}, live = s.live;
    const rows = [
      ["PROFILE", `${live.os} ${live.machine}`],
      ["CPU", `${live.cpu_physical} cores / ${live.cpu_logical} threads`],
      ["RAM", `${n1(live.ram_available_gb)} GB free / ${n1(live.ram_total_gb)} GB`],
      ["HEAVY", m.heavy ? `${m.heavy.name} · ${m.heavy.threads} thr · ${n1(m.heavy.tok_s)} tok/s` : "not tuned"],
      ["TINY", m.tiny ? `${m.tiny.name} · ${m.tiny.threads} thr · ${n1(m.tiny.tok_s)} tok/s` : "not tuned"],
      ["GUARD", s.privacy.enabled ? "active · loopback only" : "arms on first run"],
    ];
    const body = $("sys-lines");
    body.replaceChildren(...rows.map(([k, v]) => h("div", null, h("span", "k", `> ${k.padEnd(9)}`), h("span", "v", v))));
    const last = isRunning() ? `RUNNING ${S.stack.length ? S.stack[S.stack.length - 1] : ""}` : s.ready ? "READY" : "SETUP NEEDED";
    body.append(h("div", null, h("span", "k", "> "), last, h("span", "caret")));
    const [label, dot] = isRunning() ? ["RUNNING", "dot--run"] : s.ready ? ["ONLINE", "dot--ok"] : ["SETUP NEEDED", "dot--warn"];
    setText("sys-status", `SYS_STATUS: ${label}`);
    $("sys-dot").className = `dot ${dot}`;
  }

  async function refresh() {
    try {
      const s = await api("/api/state");
      S.lastState = s;
      renderState(s);
      if (s.run && (!S.run || s.run.id !== S.run.id)) follow(s.run);
    } catch (_) {
      setText("sys-status", "SYS_STATUS: OFFLINE");
      $("sys-dot").className = "dot dot--warn";
    }
  }

  // ---------------- run following ----------------
  const isRunning = () => !!S.run && S.run.state === "running";

  function follow(run) {
    S.run = run; S.next = 0; S.stack = []; S.plan.clear(); S.started = Date.now();
    $("p-flow").replaceChildren();
    $("term-out").replaceChildren();
    $("result-out").textContent = "Waiting for the run to finish...";
    setText("result-path", "Running...");
    $("copy-result").disabled = true;
    $("result-dot").hidden = true;
    setRunUi();
    poll();
  }

  async function poll() {
    clearTimeout(S.timer);
    try {
      const d = await api(`/api/events?since=${S.next}`);
      if (!d.run) return;
      if (S.run && d.run.id !== S.run.id) return follow(d.run);
      for (const ev of d.events) onEvent(ev);
      S.next = d.next;
      S.run = d.run;
      setRunUi();
      if (d.run.state === "running") S.timer = setTimeout(poll, 300);
    } catch (_) {
      S.timer = setTimeout(poll, 1500);
    }
  }

  function setRunUi() {
    const running = isRunning();
    const btn = $("run-btn");
    btn.disabled = running || !S.ready;
    btn.textContent = running ? "Running..." : "▶ Run Squeeze Pipeline";
    const fab = $("fab");
    const state = !S.run ? "idle" : S.run.state;
    fab.className = "fab" + (state === "running" ? " fab--run" : state === "error" ? " fab--bad" : "");
    fab.setAttribute("aria-label", `Pipeline status: ${state}`);
    if (!running) setText("fab-icon", state === "done" ? "✓" : state === "error" ? "!" : "▶");
    $("live").hidden = !running;
    if (running && !S.spinTimer) {
      S.spinTimer = setInterval(() => {
        S.spinI = (S.spinI + 1) % SPIN.length;
        setText("spin", SPIN[S.spinI]);
        setText("fab-icon", SPIN[S.spinI]);
        setText("live-time", `${Math.round((Date.now() - S.started) / 1000)}s`);
      }, 120);
    } else if (!running && S.spinTimer) {
      clearInterval(S.spinTimer); S.spinTimer = 0;
    }
    if (S.lastState) renderTerm(S.lastState);
  }

  function card(cls, title, meta, ...extra) {
    const el = h("div", `ev ${cls}`, h("div", "ev__row", h("span", "ev__t", title), meta ? h("span", "ev__m", meta) : null), ...extra);
    $("p-flow").append(el);
    if (isNearBottom()) el.scrollIntoView({ block: "nearest" });
    return el;
  }
  function isNearBottom() {
    const out = document.querySelector(".output").getBoundingClientRect();
    return out.bottom - window.innerHeight < 260;
  }

  const TERM_CLASS = { privacy_banner: "ok", privacy_line: "ok", loaded: "dim", flip: "flip", pressure: "pressure", setup_done: "ok" };

  function termLine(ev) {
    if (!ev.line) return;
    let cls = TERM_CLASS[ev.type] || "";
    if (ev.type === "step") cls = ev.model;
    if (ev.type === "privacy_banner" && !ev.ok) cls = "bad";
    $("term-out").append(h("span", cls, ev.line + "\n"));
  }

  function onEvent(ev) {
    termLine(ev);
    switch (ev.type) {
      case "status": {
        if (ev.state === "start") S.stack.push(ev.msg);
        else { const i = S.stack.lastIndexOf(ev.msg); if (i >= 0) S.stack.splice(i, 1); }
        setText("live-msg", S.stack.length ? S.stack[S.stack.length - 1] : "Working...");
        break;
      }
      case "run_header":
        card("ev--dim", "RUN STARTED", `RAM free ${n1(ev.free_gb)} GB · private ${ev.private ? "ON" : "OFF"}`);
        break;
      case "privacy_banner":
        card(ev.ok ? "ev--ok" : "ev--bad", ev.ok ? "✓ PRIVATE MODE VERIFIED" : "PRIVACY GUARD FAILED",
          ev.ok ? "off-device self-test blocked" : "stop and check privacy.py");
        break;
      case "loaded":
        card("ev--dim", `LOADED ${ev.role} · ${ev.name}`, `${ev.placement} · ${ev.threads} threads · ${n1(ev.secs)}s`);
        break;
      case "plan": {
        const ol = h("ol", null);
        for (const s of ev.steps) {
          const li = h("li", null, h("b", null, s.kind), ` · ${s.task}`);
          S.plan.set(s.id, li);
          ol.append(li);
        }
        const title = h("span", null, `PLAN · heavy · ${n1(ev.seconds)}s`);
        if (ev.source === "fallback") title.append(h("span", "pill pill--warn", "FALLBACK"));
        card("ev--plan", title, `${n1(ev.tok_s)} tok/s`, ol);
        break;
      }
      case "flip":
        card("ev--flip", `⇆ FLIP ${ev.frm} → ${ev.to}`, ev.reason);
        break;
      case "pressure":
        card("ev--pressure", `⚠ MEMORY PRESSURE (${ev.reason})`, `unloading heavy · ~${ev.freed_gb} GB freed`);
        break;
      case "step": {
        const meta = h("span", null, "ctx ", h("b", null, String(ev.ctx_tokens)), ` / ${ev.budget} · ${n1(ev.tok_s)} tok/s · ${n1(ev.seconds)}s`);
        if (ev.truncated) meta.append(h("span", "pill pill--warn", "TRUNCATED"));
        const bar = h("i", null);
        bar.style.width = `${Math.min(100, (100 * ev.ctx_tokens) / Math.max(1, ev.budget))}%`;
        card(`ev--${ev.model}`, `[${ev.id}] ${ev.kind} → ${ev.model} (${ev.name})`, meta, h("div", "ctxbar", bar));
        const li = S.plan.get(ev.id);
        if (li) li.className = "done";
        break;
      }
      case "summary":
        card("ev--done", `✓ DONE in ${Math.round(ev.total)}s`, `${ev.loads} model loads · ${ev.flips} ${ev.flips === 1 ? "flip" : "flips"}`);
        break;
      case "privacy_line":
        card("ev--ok", "PRIVATE MODE · 0 connections allowed off-device", `${ev.blocked.length} blocked`);
        break;
      case "output_path": {
        const open = h("button", "chip", "Open result.md");
        open.type = "button";
        open.addEventListener("click", () => selectTab("t-result"));
        card("ev--dim", "OUTPUT", ev.line.replace(/^Output:\s*/, ""), open);
        break;
      }
      case "end":
        S.stack = [];
        if (ev.state === "error") card("ev--bad", "RUN FAILED", null, h("div", null, ev.error || "unknown error"));
        if (ev.state === "done") loadResult();
        else setText("result-path", "Run failed, no result");
        refresh();
        break;
      default:
        break;
    }
  }

  async function loadResult() {
    try {
      const r = await api("/api/result");
      $("result-out").textContent = r.text;
      setText("result-path", r.path);
      $("copy-result").disabled = false;
      $("result-dot").hidden = $("t-result").getAttribute("aria-selected") === "true";
    } catch (_) {
      setText("result-path", "Could not load result.md");
    }
  }

  // ---------------- tabs ----------------
  const TABS = ["t-flow", "t-term", "t-result"];
  function selectTab(id) {
    for (const t of TABS) {
      const on = t === id, tab = $(t);
      tab.setAttribute("aria-selected", String(on));
      tab.tabIndex = on ? 0 : -1;
      $(tab.getAttribute("aria-controls")).hidden = !on;
    }
    if (id === "t-result") $("result-dot").hidden = true;
  }

  // ---------------- form ----------------
  function showMsg(text) { const m = $("form-msg"); m.textContent = text; m.hidden = !text; }

  async function submit(e) {
    e.preventDefault();
    showMsg("");
    const goal = $("goal").value.trim();
    if (!goal) { showMsg("Enter a task goal first."); $("goal").focus(); return; }
    const raw = $("opt-minfree").value.trim();
    const minFree = raw === "" ? null : Number(raw);
    if (minFree !== null && !(minFree > 0 && minFree <= 1024)) { showMsg("Free-RAM trigger must be between 0 and 1024 GB."); return; }
    $("run-btn").disabled = true;
    try {
      const r = await api("/api/run", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal, simulate_pressure: $("opt-pressure").checked, min_free_gb: minFree }),
      });
      selectTab("t-flow");
      follow(r.run);
    } catch (err) {
      showMsg(err.message);
      $("run-btn").disabled = !S.ready;
    }
  }

  function updateCount() { setText("goal-count", `${$("goal").value.length} / 2000`); }

  function init() {
    const goal = $("goal");
    goal.value = store.get("squeeze.goal") || DEMO;
    updateCount();
    goal.addEventListener("input", () => { store.set("squeeze.goal", goal.value); updateCount(); });
    $("demo-task").addEventListener("click", () => { goal.value = DEMO; store.set("squeeze.goal", DEMO); updateCount(); goal.focus(); });
    $("run-form").addEventListener("submit", submit);
    $("copy-result").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText($("result-out").textContent); setText("copy-result", "Copied"); }
      catch (_) { setText("copy-result", "Copy failed"); }
      setTimeout(() => setText("copy-result", "Copy"), 1500);
    });
    for (const id of TABS) $(id).addEventListener("click", () => selectTab(id));
    document.querySelector(".tabs").addEventListener("keydown", (e) => {
      const i = TABS.indexOf(document.activeElement.id);
      if (i < 0 || (e.key !== "ArrowRight" && e.key !== "ArrowLeft")) return;
      const next = TABS[(i + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length];
      selectTab(next); $(next).focus(); e.preventDefault();
    });
    document.querySelectorAll("[data-focus-goal]").forEach((a) => a.addEventListener("click", () => setTimeout(() => goal.focus({ preventScroll: true }), 350)));
    document.querySelectorAll("[data-tab]").forEach((a) => a.addEventListener("click", () => selectTab(a.dataset.tab)));
    refresh();
    setInterval(() => { if (!document.hidden && !isRunning()) refresh(); }, 5000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
