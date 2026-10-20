/* Wearable Exercise Physiology — interactive charts and animation (D3 v7) */
(function () {
  "use strict";
  const isStatic = /[?&]static/.test(location.search);   // ?static: no motion (screenshots, preference)
  const reduce = isStatic || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (isStatic) document.documentElement.classList.add("no-motion");
  const DUR = reduce ? 0 : 900;
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const fmt = (v, k = 2) => (v == null || !isFinite(v) ? "–" : (+v).toFixed(k));
  const signed = (v, k = 1) => (v == null ? "–" : (v > 0 ? "+" : "") + (+v).toFixed(k));

  /* ---------- tooltip ---------- */
  const tip = document.createElement("div");
  tip.className = "tooltip";
  document.body.appendChild(tip);
  function showTip(evt, html) {
    tip.innerHTML = html;
    tip.style.opacity = 1;
    const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + w > window.innerWidth - 8) x = evt.clientX - w - pad;
    if (y + h > window.innerHeight - 8) y = evt.clientY - h - pad;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  const hideTip = () => (tip.style.opacity = 0);

  /* ---------- theme toggle ---------- */
  const root = document.documentElement;
  try { const s = localStorage.getItem("theme"); if (s) root.setAttribute("data-theme", s); } catch (e) {}
  document.getElementById("themeBtn").addEventListener("click", () => {
    const dark = root.getAttribute("data-theme") === "dark" ||
      (!root.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
    const next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (e) {}
    redrawAll(false);
  });

  /* ---------- hero pulse (synthetic PPG-like wave) ---------- */
  (function pulse() {
    const svg = document.querySelector(".pulse");
    if (!svg) return;
    const path = svg.querySelector("path");
    let t0 = 0;
    function wave(x, t) {
      const ph = (x * 0.012 + t) % 1;                // one beat every ~83 px
      const sys = Math.exp(-Math.pow((ph - 0.18) / 0.06, 2));
      const dic = 0.35 * Math.exp(-Math.pow((ph - 0.42) / 0.07, 2));
      return sys + dic;
    }
    function frame(ts) {
      const box = svg.getBoundingClientRect();
      const W = Math.round(box.width) || 1200, H = Math.round(box.height) || 220;
      svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
      const t = reduce ? 0 : (ts - t0) / 1400;
      let d = "";
      for (let x = 0; x <= W; x += 4) {
        const y = H * 0.75 - wave(x, -t) * H * 0.45;
        d += (x ? "L" : "M") + x + "," + y.toFixed(1);
      }
      path.setAttribute("d", d);
      path.setAttribute("stroke", css("--stress"));
      if (!reduce) requestAnimationFrame(frame);
    }
    requestAnimationFrame((ts) => { t0 = ts; frame(ts); });
  })();

  /* ---------- reveal + counters ---------- */
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add("in");
      e.target.querySelectorAll("[data-count]").forEach(countUp);
      io.unobserve(e.target);
    });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));

  function countUp(el, instant) {
    if (el.dataset.done) return;
    el.dataset.done = 1;
    const end = parseFloat(el.dataset.count), dec = +(el.dataset.decimals || 0);
    const pre = el.dataset.prefix || "", suf = el.dataset.suffix || "";
    const show = (v) => (el.textContent = pre + v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + suf);
    if (reduce || instant) return show(end);
    const t0 = performance.now(), dur = 1400;
    (function step(now) {
      const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      show(end * e);
      if (p < 1) requestAnimationFrame(step);
    })(t0);
  }

  /* ---------- helpers ---------- */
  const charts = [];
  function register(id, draw, initial) {
    const el = document.getElementById(id);
    if (!el) return;
    const c = { el, draw, state: initial, drawn: false };
    charts.push(c);
    const ob = new IntersectionObserver((en) => {
      if (en[0].isIntersecting && !c.drawn) { c.drawn = true; c.draw(c.el, c.state, true); ob.disconnect(); }
    }, { threshold: 0.15 });
    ob.observe(el);
    const ctl = document.querySelector(`[data-controls="${id}"]`);
    if (ctl) ctl.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      ctl.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      c.state = b.dataset.value; c.drawn = true; c.draw(c.el, c.state, true);
    }));
  }
  function redrawAll(animate) { charts.forEach((c) => c.drawn && c.draw(c.el, c.state, animate)); }
  let rt; window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => redrawAll(false), 200); });

  function frame(el, height, m) {
    el.innerHTML = "";
    const W = Math.max(300, el.clientWidth), H = height;
    const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img");
    return { svg, W, H, iw: W - m.l - m.r, ih: H - m.t - m.b, g: svg.append("g").attr("transform", `translate(${m.l},${m.t})`) };
  }
  const isNarrow = () => window.innerWidth < 720;
  const COND = () => ({ STRESS: css("--stress"), AEROBIC: css("--aerobic"), ANAEROBIC: css("--anaerobic") });

  /* transition only when animating; otherwise set attributes immediately
     (d3 transitions need requestAnimationFrame, which hidden pages pause) */
  d3.selection.prototype.maybe = function (anim, delay) {
    return anim && !reduce ? this.transition().duration(DUR).delay(delay || 0) : this;
  };

  /* ================= charts ================= */
  function drawAll(D) {
    const STATE_LABEL = {
      SEATED_BASELINE: "Seated baseline", SEATED_REST: "Seated rest", STRESS_TASK: "Stress task",
      UNLOADED_PEDALLING: "Unloaded pedalling", AEROBIC_STAGE: "Aerobic stage", SPRINT: "Sprint",
      POST_EXERCISE_REST: "Post-exercise rest", REST_SEATED: "Seated rest", STRESS_TMCT: "Stress (TMCT)",
      STRESS_RECOVERY: "Stress recovery", AEROBIC_MODERATE: "Aerobic moderate", AEROBIC_PEAK: "Aerobic peak",
      POST_SPRINT: "Post-sprint 0–2 min"
    };
    const stateColor = (s) => {
      const c = COND();
      if (/STRESS|SEATED|REST_SEATED/.test(s) && !/POST/.test(s)) return c.STRESS;
      if (/SPRINT/.test(s)) return c.ANAEROBIC;
      if (/AEROBIC|PEDAL/.test(s)) return c.AEROBIC;
      return css("--ink-3");
    };

    /* 1 · HR validity by state */
    register("chart-validity", (el, _s, anim) => {
      const reasons = ["valid", "low PPG quality", "HR disagrees with PPG", "cadence lock-in", "no HR"];
      const col = { "valid": css("--stress"), "low PPG quality": css("--ink-3"), "HR disagrees with PPG": "#e8b4a0",
                    "cadence lock-in": css("--anaerobic"), "no HR": css("--rule") };
      const data = D.hr_validity;
      const m = { t: 6, r: 12, b: 26, l: isNarrow() ? 118 : 150 };
      const f = frame(el, data.length * 38 + m.t + m.b, m);
      const x = d3.scaleLinear([0, 1], [0, f.iw]);
      const y = d3.scaleBand(data.map((d) => d.state), [0, f.ih]).padding(0.28);
      f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(5, "%"));
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickFormat((s) => STATE_LABEL[s]).tickSize(0)).select(".domain").remove();
      data.forEach((d) => {
        let acc = 0;
        reasons.forEach((r) => {
          const v = d[r] || 0, x0 = acc; acc += v;
          const rect = f.g.append("rect").attr("y", y(d.state)).attr("height", y.bandwidth()).attr("x", x(x0))
            .attr("width", anim ? 0 : Math.max(0, x(v) - 2)).attr("rx", 3).attr("fill", col[r])
            .on("mousemove", (e) => showTip(e, `<b>${STATE_LABEL[d.state]}</b><br>${r}: ${(v * 100).toFixed(0)}% of windows`))
            .on("mouseleave", hideTip);
          rect.maybe(anim, reasons.indexOf(r) * 120).attr("width", Math.max(0, x(v) - 2));
        });
        f.g.append("text").attr("x", 6).attr("y", y(d.state) + y.bandwidth() / 2).attr("dy", "0.35em")
          .style("font-size", "11px").style("font-weight", 700).style("fill", d.valid > 0.08 ? "#fff" : css("--ink"))
          .text((d.valid * 100).toFixed(0) + "%");
      });
      const lg = document.getElementById("legend-validity");
      lg.innerHTML = reasons.map((r) => `<span><i style="background:${col[r]}"></i>${r}</span>`).join("");
    });

    /* 2 · Event-locked responses */
    const SIG = { HR: ["Δ heart rate", "bpm"], EDA: ["Δ EDA", "µS"], Movement: ["Δ movement", "g"], TEMP: ["Δ skin temperature", "°C"] };
    register("chart-event", (el, sig, anim) => {
      el.innerHTML = "";
      const panels = [["tmct", "Stress task (TMCT) onset", COND().STRESS, 193], ["sprint", "Sprint onset", COND().ANAEROBIC, 32]];
      const wrap = d3.select(el).append("div").style("display", "grid").style("gap", "16px")
        .style("grid-template-columns", isNarrow() ? "1fr" : "1fr 1fr");
      panels.forEach(([key, title, color, dur]) => {
        const data = D.event_locked[key][sig] || [];
        const box = wrap.append("div").node();
        d3.select(box).append("div").style("font-weight", 600).style("font-size", "14px").style("margin-bottom", "2px").text(title);
        const m = { t: 10, r: 14, b: 32, l: 46 };
        const f = frame(box, 250, m);
        f.svg.select("g").remove();
        const g = f.svg.append("g").attr("transform", `translate(${m.l},${m.t})`);
        const x = d3.scaleLinear([-60, 245], [0, f.iw]);
        const ext = d3.extent(data.flatMap((d) => [d.low, d.high, 0]).filter((v) => v != null));
        const y = d3.scaleLinear(ext[0] === undefined ? [0, 1] : ext, [f.ih, 0]).nice();
        g.append("rect").attr("x", x(0)).attr("width", x(dur) - x(0)).attr("height", f.ih).attr("fill", color).attr("opacity", 0.09);
        g.append("g").attr("class", "grid").call(d3.axisLeft(y).ticks(5).tickSize(-f.iw).tickFormat(""));
        g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(6))
          .append("text").attr("x", f.iw).attr("y", 28).attr("text-anchor", "end").style("fill", css("--ink-3")).text("seconds from onset");
        g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(5));
        g.append("line").attr("x1", 0).attr("x2", f.iw).attr("y1", y(0)).attr("y2", y(0)).attr("stroke", css("--ink-3"));
        if (!data.length) { g.append("text").attr("x", f.iw / 2).attr("y", f.ih / 2).attr("text-anchor", "middle").text("not enough valid data"); return; }
        const segs = [];
        let cur = [];
        data.forEach((d, i) => { if (i && d.t - data[i - 1].t > 6) { segs.push(cur); cur = []; } cur.push(d); });
        segs.push(cur);
        segs.forEach((s) => {
          g.append("path").datum(s).attr("fill", color).attr("opacity", 0.2)
            .attr("d", d3.area().x((d) => x(d.t)).y0((d) => y(d.low)).y1((d) => y(d.high)));
          const p = g.append("path").datum(s).attr("fill", "none").attr("stroke", color).attr("stroke-width", 2.2)
            .attr("d", d3.line().x((d) => x(d.t)).y((d) => y(d.mean)));
          if (anim && !reduce) {
            const L = p.node().getTotalLength();
            p.attr("stroke-dasharray", `${L} ${L}`).attr("stroke-dashoffset", L).transition().duration(1400).ease(d3.easeCubicOut).attr("stroke-dashoffset", 0);
          }
        });
        const focus = g.append("g").style("display", "none");
        focus.append("line").attr("y1", 0).attr("y2", f.ih).attr("stroke", css("--ink-3"));
        focus.append("circle").attr("r", 4.5).attr("fill", color).attr("stroke", css("--surface")).attr("stroke-width", 2);
        g.append("rect").attr("width", f.iw).attr("height", f.ih).attr("fill", "transparent")
          .on("mousemove", (e) => {
            const tx = x.invert(d3.pointer(e)[0]);
            const d = data.reduce((a, b) => (Math.abs(b.t - tx) < Math.abs(a.t - tx) ? b : a));
            focus.style("display", null).attr("transform", `translate(${x(d.t)},0)`);
            focus.select("circle").attr("cy", y(d.mean));
            showTip(e, `<b>${d.t.toFixed(0)} s</b> from onset<br>${SIG[sig][0]}: <b>${signed(d.mean, sig === "Movement" ? 3 : 2)} ${SIG[sig][1]}</b><br>95% CI ${fmt(d.low, sig === "Movement" ? 3 : 2)} to ${fmt(d.high, sig === "Movement" ? 3 : 2)}<br>n = ${d.n} participants`);
          })
          .on("mouseleave", () => { focus.style("display", "none"); hideTip(); });
      });
    }, "HR");

    /* 3 · Change from rest (forest) */
    const FEAT = { hr_mean: ["Heart rate", "bpm", 1], eda_log: ["EDA tonic (log10 µS)", "log10 µS", 2],
                   eda_scr_rate: ["SCR rate", "per min", 2], temp_slope: ["Skin-temp slope", "°C/min", 3], acc_movement: ["Wrist movement", "g", 3] };
    register("chart-forest", (el, feat, anim) => {
      const data = D.vs_rest.filter((d) => d.feature === feat);
      const m = { t: 8, r: 70, b: 34, l: isNarrow() ? 130 : 160 };
      const f = frame(el, data.length * 40 + m.t + m.b, m);
      const lo = d3.min(data, (d) => d.ci_low), hi = d3.max(data, (d) => d.ci_high);
      const x = d3.scaleLinear([Math.min(0, lo), Math.max(0, hi)], [0, f.iw]).nice();
      const y = d3.scaleBand(data.map((d) => d.state), [0, f.ih]).padding(0.4);
      f.g.append("g").attr("class", "grid").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(6).tickSize(-f.ih).tickFormat(""));
      f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(6))
        .append("text").attr("x", f.iw).attr("y", 30).attr("text-anchor", "end").style("fill", css("--ink-3")).text(`change from seated rest (${FEAT[feat][1]})`);
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickFormat((s) => STATE_LABEL[s]).tickSize(0)).select(".domain").remove();
      f.g.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", 0).attr("y2", f.ih).attr("stroke", css("--ink"));
      data.forEach((d, i) => {
        const cy = y(d.state) + y.bandwidth() / 2, c = stateColor(d.state);
        const line = f.g.append("line").attr("y1", cy).attr("y2", cy).attr("x1", x(0)).attr("x2", x(0)).attr("stroke", c).attr("stroke-width", 3).attr("stroke-linecap", "round");
        const dot = f.g.append("circle").attr("cy", cy).attr("cx", x(0)).attr("r", 6).attr("fill", c).attr("stroke", css("--surface")).attr("stroke-width", 2);
        const t = anim ? DUR : 0;
        line.maybe(anim, i * 70).attr("x1", x(d.ci_low)).attr("x2", x(d.ci_high));
        dot.maybe(anim, i * 70).attr("cx", x(d.mean_diff));
        f.g.append("text").attr("x", f.iw + 8).attr("y", cy).attr("dy", "0.35em").style("font-size", "11px").style("fill", css("--ink-3")).text(`n=${d.n}`);
        f.g.append("rect").attr("x", 0).attr("width", f.iw).attr("y", y(d.state) - 6).attr("height", y.bandwidth() + 12).attr("fill", "transparent")
          .on("mousemove", (e) => showTip(e, `<b>${STATE_LABEL[d.state]}</b><br>${FEAT[feat][0]}: <b>${signed(d.mean_diff, FEAT[feat][2])}</b> ${FEAT[feat][1]}<br>95% CI ${fmt(d.ci_low, FEAT[feat][2])} to ${fmt(d.ci_high, FEAT[feat][2])}<br>Cohen's d<sub>z</sub> ${fmt(d.dz)} · Holm p ${d.p_holm < 0.001 ? "< 0.001" : fmt(d.p_holm, 3)}<br>n = ${d.n} participants`))
          .on("mouseleave", hideTip);
      });
    }, "hr_mean");

    /* 4 · Aerobic stages, participant lines */
    const AER = { hr_mean: ["Heart rate", "bpm"], eda_tonic_mean: ["EDA tonic", "µS"], temp_mean: ["Skin temperature", "°C"], acc_movement: ["Wrist movement", "g"] };
    register("chart-aerobic", (el, v, anim) => {
      const rows = D.aerobic.filter((d) => d[v] != null);
      const bySub = d3.groups(rows, (d) => d.subject_id).map(([s, a]) => [s, a.sort((p, q) => p.rpm - q.rpm)]);
      const rpms = [...new Set(D.aerobic.map((d) => d.rpm))].sort((a, b) => a - b);
      const med = rpms.map((r) => ({ rpm: r, v: d3.median(rows.filter((d) => d.rpm === r), (d) => d[v]) })).filter((d) => d.v != null);
      const m = { t: 10, r: 16, b: 34, l: 50 };
      const f = frame(el, 300, m);
      const x = d3.scalePoint(rpms, [0, f.iw]).padding(0.2);
      const y = d3.scaleLinear(d3.extent(rows, (d) => d[v]), [f.ih, 0]).nice();
      f.g.append("g").attr("class", "grid").call(d3.axisLeft(y).ticks(5).tickSize(-f.iw).tickFormat(""));
      f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x))
        .append("text").attr("x", f.iw).attr("y", 30).attr("text-anchor", "end").style("fill", css("--ink-3")).text("prescribed cadence (rpm)");
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(5));
      const line = d3.line().x((d) => x(d.rpm)).y((d) => y(d[v]));
      const col = COND().AEROBIC;
      const paths = f.g.append("g").selectAll("path").data(bySub).join("path").attr("fill", "none").attr("stroke", col)
        .attr("stroke-width", 1.4).attr("opacity", 0.32).attr("d", (d) => line(d[1]))
        .on("mousemove", function (e, d) {
          paths.attr("opacity", 0.12); d3.select(this).attr("opacity", 1).attr("stroke-width", 2.6).raise();
          const last = d[1][d[1].length - 1];
          showTip(e, `<b>${d[0]}</b><br>${d[1].length} stages with valid data<br>at ${last.rpm} rpm: ${fmt(last[v], v === "acc_movement" ? 3 : 1)} ${AER[v][1]}`);
        })
        .on("mouseleave", function () { paths.attr("opacity", 0.32).attr("stroke-width", 1.4); hideTip(); });
      const mp = f.g.append("path").datum(med).attr("fill", "none").attr("stroke", css("--ink")).attr("stroke-width", 3)
        .attr("d", d3.line().x((d) => x(d.rpm)).y((d) => y(d.v))).style("pointer-events", "none");
      f.g.selectAll(".md").data(med).join("circle").attr("cx", (d) => x(d.rpm)).attr("cy", (d) => y(d.v)).attr("r", 4).attr("fill", css("--ink")).style("pointer-events", "none");
      if (anim && !reduce) { const L = mp.node().getTotalLength(); mp.attr("stroke-dasharray", `${L} ${L}`).attr("stroke-dashoffset", L).transition().duration(1400).attr("stroke-dashoffset", 0); }
    }, "hr_mean");

    /* 5 · Individual stress responses */
    register("chart-individual", (el, k, anim) => {
      const data = D.individual.filter((d) => d[k] != null).sort((a, b) => a[k] - b[k]);
      const m = { t: 8, r: 16, b: 34, l: 40 };
      const f = frame(el, Math.max(300, data.length * 12 + m.t + m.b), m);
      const x = d3.scaleLinear(d3.extent([0, ...data.map((d) => d[k])]), [0, f.iw]).nice();
      const y = d3.scaleBand(data.map((d) => d.subject_id), [f.ih, 0]).padding(0.25);
      f.g.append("g").attr("class", "grid").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(6).tickSize(-f.ih).tickFormat(""));
      f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(6))
        .append("text").attr("x", f.iw).attr("y", 30).attr("text-anchor", "end").style("fill", css("--ink-3"))
        .text(k === "dHR" ? "Δ HR, TMCT − seated rest (bpm)" : "Δ EDA tonic, TMCT − seated rest (µS)");
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickSize(0)).selectAll("text").style("font-size", "9px");
      f.g.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", 0).attr("y2", f.ih).attr("stroke", css("--ink"));
      data.forEach((d, i) => {
        const cy = y(d.subject_id) + y.bandwidth() / 2, c = d[k] > 0 ? COND().STRESS : css("--ink-3");
        const ln = f.g.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", cy).attr("y2", cy).attr("stroke", c).attr("stroke-width", 2.2);
        const dot = f.g.append("circle").attr("cx", x(0)).attr("cy", cy).attr("r", 4).attr("fill", c);
        const t = anim ? DUR : 0;
        ln.maybe(anim, i * 18).attr("x2", x(d[k]));
        dot.maybe(anim, i * 18).attr("cx", x(d[k]));
        f.g.append("rect").attr("x", 0).attr("width", f.iw).attr("y", y(d.subject_id)).attr("height", y.bandwidth()).attr("fill", "transparent")
          .on("mousemove", (e) => showTip(e, `<b>${d.subject_id}</b> (cohort ${d.cohort})<br>${k === "dHR" ? "Δ HR" : "Δ EDA"}: <b>${signed(d[k], 2)}</b> ${k === "dHR" ? "bpm" : "µS"}`))
          .on("mouseleave", hideTip);
      });
      const up = data.filter((d) => d[k] > 0).length;
      document.getElementById("note-individual").textContent =
        `${up} of ${data.length} participants increase · median ${signed(d3.median(data, (d) => d[k]), 2)} ${k === "dHR" ? "bpm" : "µS"}`;
    }, "dHR");

    /* 6 · Multimodal profile heatmap */
    register("chart-profile", (el) => {
      const P = D.profile, feats = { hr_mean: "HR (bpm)", eda_tonic_mean: "EDA tonic (µS)", eda_scr_rate: "SCR / min", temp_slope: "Skin-temp slope (°C/min)", acc_movement: "Movement (g)" };
      const cols = P.features.map((f, j) => {
        const vals = P.values.map((r) => r[j]).filter((v) => v != null);
        return { mean: d3.mean(vals), sd: d3.deviation(vals) };
      });
      const m = { t: 8, r: 8, b: isNarrow() ? 70 : 46, l: isNarrow() ? 120 : 170 };
      const f = frame(el, P.features.length * 46 + m.t + m.b, m);
      const x = d3.scaleBand(P.states, [0, f.iw]).padding(0.04);
      const y = d3.scaleBand(P.features, [0, f.ih]).padding(0.06);
      const color = (z) => d3.interpolateRdBu(0.5 - Math.max(-2, Math.min(2, z)) / 4);
      P.states.forEach((s, i) => P.features.forEach((ft, j) => {
        const v = P.values[i][j], z = v == null ? null : (v - cols[j].mean) / cols[j].sd;
        f.g.append("rect").attr("x", x(s)).attr("y", y(ft)).attr("width", x.bandwidth()).attr("height", y.bandwidth()).attr("rx", 4)
          .attr("fill", z == null ? css("--surface-2") : color(z))
          .on("mousemove", (e) => showTip(e, `<b>${STATE_LABEL[s]}</b><br>${feats[ft]}: <b>${v == null ? "n < 10" : fmt(v, Math.abs(v) < 10 ? 2 : 0)}</b>${z == null ? "" : `<br>z = ${fmt(z, 2)} across states`}`))
          .on("mouseleave", hideTip);
        if (!isNarrow() || x.bandwidth() > 34)
          f.g.append("text").attr("x", x(s) + x.bandwidth() / 2).attr("y", y(ft) + y.bandwidth() / 2).attr("dy", "0.35em").attr("text-anchor", "middle")
            .style("font-size", "10.5px").style("pointer-events", "none").style("fill", z != null && Math.abs(z) > 1.2 ? "#fff" : "#222")
            .text(v == null ? "–" : fmt(v, Math.abs(v) < 10 ? 2 : 0));
      }));
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickFormat((d) => feats[d]).tickSize(0)).select(".domain").remove();
      const ax = f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).tickFormat((d) => STATE_LABEL[d]).tickSize(0));
      ax.select(".domain").remove();
      ax.selectAll("text").attr("transform", isNarrow() ? "rotate(-40)" : null).style("text-anchor", isNarrow() ? "end" : "middle").attr("dy", isNarrow() ? "0.4em" : "1.2em");
    });

    /* 7 · ICC heatmap */
    register("chart-icc", (el) => {
      const I = D.icc, lab = { hr_mean: "Heart rate", eda_log: "EDA tonic", eda_scr_rate: "SCR rate", temp_slope: "Skin-temp slope", acc_movement: "Movement" };
      const m = { t: 8, r: 8, b: isNarrow() ? 70 : 40, l: 120 };
      const f = frame(el, I.features.length * 40 + m.t + m.b, m);
      const x = d3.scaleBand(I.states, [0, f.iw]).padding(0.05), y = d3.scaleBand(I.features, [0, f.ih]).padding(0.07);
      I.features.forEach((ft, i) => I.states.forEach((s, j) => {
        const v = I.values[i][j];
        f.g.append("rect").attr("x", x(s)).attr("y", y(ft)).attr("width", x.bandwidth()).attr("height", y.bandwidth()).attr("rx", 4)
          .attr("fill", v == null ? css("--surface-2") : d3.interpolateBlues(0.1 + 0.85 * v))
          .on("mousemove", (e) => showTip(e, `<b>${lab[ft]} · ${STATE_LABEL[s]}</b><br>ICC = ${fmt(v)}<br>${Math.round((v || 0) * 100)}% of window-to-window variance is between people`))
          .on("mouseleave", hideTip);
        f.g.append("text").attr("x", x(s) + x.bandwidth() / 2).attr("y", y(ft) + y.bandwidth() / 2).attr("dy", "0.35em").attr("text-anchor", "middle")
          .style("font-size", "11px").style("pointer-events", "none").style("fill", v > 0.6 ? "#fff" : "#222").text(fmt(v));
      }));
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickFormat((d) => lab[d]).tickSize(0)).select(".domain").remove();
      const ax = f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).tickFormat((d) => STATE_LABEL[d]).tickSize(0));
      ax.select(".domain").remove();
      ax.selectAll("text").attr("transform", isNarrow() ? "rotate(-40)" : null).style("text-anchor", isNarrow() ? "end" : "middle").attr("dy", isNarrow() ? "0.4em" : "1.2em");
    });

    /* 8 · Leakage */
    register("chart-leakage", (el, _s, anim) => {
      const data = D.leakage.map((d) => ({ ...d, short: /leaky/i.test(d.validation) ? "Random window split (leaky)" : "Leave-one-subject-out" }));
      const m = { t: 6, r: 50, b: 28, l: isNarrow() ? 150 : 200 };
      const f = frame(el, 130, m);
      const x = d3.scaleLinear([0, 1], [0, f.iw]), y = d3.scaleBand(data.map((d) => d.short), [0, f.ih]).padding(0.3);
      f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(5));
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickSize(0)).select(".domain").remove();
      data.forEach((d, i) => {
        const c = i === 0 ? css("--ink-3") : css("--accent");
        f.g.append("rect").attr("y", y(d.short)).attr("height", y.bandwidth()).attr("x", 0).attr("rx", 4).attr("fill", c)
          .attr("width", anim ? 0 : x(d.macro_f1)).maybe(anim, i * 250).attr("width", x(d.macro_f1));
        f.g.append("text").attr("x", x(d.macro_f1) + 6).attr("y", y(d.short) + y.bandwidth() / 2).attr("dy", "0.35em")
          .style("font-weight", 700).style("fill", css("--ink")).text(fmt(d.macro_f1));
      });
    });

    /* 9 · Ablation (task toggle) */
    register("chart-ablation", (el, task, anim) => {
      const order3 = ["Skin temperature", "EDA", "Heart rate", "Physiology (HR+EDA+TEMP)", "Movement (ACC)", "All signals"];
      const data = task === "three" ? order3.map((n) => D.ablation.find((d) => d.feature_set === n))
        : ["Movement (ACC)", "Heart rate", "EDA", "Physiology (HR+EDA+TEMP)", "All signals"].map((n) => D.stress_rest.find((d) => d.feature_set === n));
      const chance = task === "three" ? 1 / 3 : 0.5;
      const m = { t: 8, r: 52, b: 34, l: isNarrow() ? 150 : 190 };
      const f = frame(el, data.length * 40 + m.t + m.b, m);
      const x = d3.scaleLinear([0.2, 0.9], [0, f.iw]), y = d3.scaleBand(data.map((d) => d.feature_set), [0, f.ih]).padding(0.4);
      f.g.append("g").attr("class", "grid").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(7).tickSize(-f.ih).tickFormat(""));
      f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(7))
        .append("text").attr("x", f.iw).attr("y", 30).attr("text-anchor", "end").style("fill", css("--ink-3")).text("macro-F1 in unseen participants (95% CI)");
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickSize(0)).select(".domain").remove();
      f.g.append("line").attr("x1", x(chance)).attr("x2", x(chance)).attr("y1", 0).attr("y2", f.ih).attr("stroke", css("--ink-3")).attr("stroke-dasharray", "0");
      f.g.append("text").attr("x", x(chance) + 4).attr("y", 10).style("font-size", "10px").style("fill", css("--ink-3")).text("chance");
      const colorOf = (n) => n === "All signals" ? css("--ink") : n.startsWith("Movement") ? css("--aerobic") : n.startsWith("Physiology") ? css("--stress") : css("--ink-3");
      data.forEach((d, i) => {
        const cy = y(d.feature_set) + y.bandwidth() / 2, c = colorOf(d.feature_set), t = anim ? DUR : 0;
        f.g.append("line").attr("y1", cy).attr("y2", cy).attr("x1", x(0.2)).attr("x2", x(0.2)).attr("stroke", c).attr("stroke-width", 3.5).attr("stroke-linecap", "round")
          .maybe(anim, i * 90).attr("x1", x(d.macro_f1_low)).attr("x2", x(d.macro_f1_high));
        f.g.append("circle").attr("cy", cy).attr("cx", x(0.2)).attr("r", 6.5).attr("fill", c).attr("stroke", css("--surface")).attr("stroke-width", 2)
          .maybe(anim, i * 90).attr("cx", x(d.macro_f1));
        f.g.append("text").attr("x", x(d.macro_f1_high) + 8).attr("y", cy).attr("dy", "0.35em").style("font-weight", 700).style("font-size", "12px").style("fill", css("--ink"))
          .style("opacity", anim && !reduce ? 0 : 1).text(fmt(d.macro_f1)).maybe(anim, DUR + i * 90).style("opacity", 1);
        f.g.append("rect").attr("x", 0).attr("width", f.iw).attr("y", y(d.feature_set) - 6).attr("height", y.bandwidth() + 12).attr("fill", "transparent")
          .on("mousemove", (e) => showTip(e, `<b>${d.feature_set}</b><br>macro-F1 ${fmt(d.macro_f1)} (95% CI ${fmt(d.macro_f1_low)}–${fmt(d.macro_f1_high)})<br>balanced accuracy ${fmt(d.balanced_accuracy)}`))
          .on("mouseleave", hideTip);
      });
    }, "three");

    /* 10 · Missingness shortcut */
    register("chart-shortcut", (el, _s, anim) => {
      const data = D.shortcut;
      const m = { t: 6, r: 48, b: 30, l: isNarrow() ? 170 : 230 };
      const f = frame(el, data.length * 36 + m.t + m.b, m);
      const x = d3.scaleLinear([0, 0.8], [0, f.iw]), y = d3.scaleBand(data.map((d) => d.feature_set), [0, f.ih]).padding(0.3);
      f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(4));
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickSize(0)).select(".domain").remove();
      data.forEach((d, i) => {
        const hl = /HR-missing indicator$/.test(d.feature_set) || d.feature_set === "Movement + HR-missing indicator";
        const c = d.feature_set === "All signals" ? css("--ink") : hl ? css("--anaerobic") : css("--ink-3");
        f.g.append("rect").attr("y", y(d.feature_set)).attr("height", y.bandwidth()).attr("x", 0).attr("rx", 4).attr("fill", c)
          .attr("width", anim ? 0 : x(d.macro_f1)).maybe(anim, i * 120).attr("width", x(d.macro_f1));
        f.g.append("text").attr("x", x(d.macro_f1) + 6).attr("y", y(d.feature_set) + y.bandwidth() / 2).attr("dy", "0.35em")
          .style("font-weight", 700).style("font-size", "12px").style("fill", css("--ink")).text(fmt(d.macro_f1));
        f.g.append("rect").attr("x", 0).attr("width", f.iw).attr("y", y(d.feature_set)).attr("height", y.bandwidth()).attr("fill", "transparent")
          .on("mousemove", (e) => showTip(e, `<b>${d.feature_set}</b><br>macro-F1 ${fmt(d.macro_f1)} · balanced accuracy ${fmt(d.balanced_accuracy)}<br>anaerobic recall ${fmt(d.recall_ANAEROBIC)}`))
          .on("mouseleave", hideTip);
      });
    });

    /* 11 · Confusion matrix */
    register("chart-confusion", (el, set) => {
      const M = D.confusion[set], cls = D.classes;
      const m = { t: 28, r: 8, b: 8, l: 90 };
      const side = Math.min(el.clientWidth - m.l - m.r, 380);
      el.innerHTML = "";
      const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${side + m.l + m.r} ${side + m.t + m.b + 20}`).style("max-width", "520px");
      const g = svg.append("g").attr("transform", `translate(${m.l},${m.t})`);
      const b = d3.scaleBand(cls, [0, side]).padding(0.05);
      M.forEach((row, i) => {
        const tot = d3.sum(row);
        row.forEach((v, j) => {
          const p = v / tot;
          g.append("rect").attr("x", b(cls[j])).attr("y", b(cls[i])).attr("width", b.bandwidth()).attr("height", b.bandwidth()).attr("rx", 6)
            .attr("fill", d3.interpolateBlues(0.06 + 0.88 * p))
            .on("mousemove", (e) => showTip(e, `True <b>${cls[i].toLowerCase()}</b> predicted as <b>${cls[j].toLowerCase()}</b><br>${(p * 100).toFixed(0)}% of ${tot.toLocaleString()} windows (${v.toLocaleString()})`))
            .on("mouseleave", hideTip);
          g.append("text").attr("x", b(cls[j]) + b.bandwidth() / 2).attr("y", b(cls[i]) + b.bandwidth() / 2).attr("text-anchor", "middle").attr("dy", "0.35em")
            .style("font-weight", 700).style("font-size", "15px").style("pointer-events", "none").style("fill", p > 0.55 ? "#fff" : "#1b1b1b").text((p * 100).toFixed(0) + "%");
        });
      });
      cls.forEach((c) => {
        g.append("text").attr("x", b(c) + b.bandwidth() / 2).attr("y", -10).attr("text-anchor", "middle").style("font-size", "12px").text(c.toLowerCase());
        g.append("text").attr("x", -8).attr("y", b(c) + b.bandwidth() / 2).attr("text-anchor", "end").attr("dy", "0.35em").style("font-size", "12px").text(c.toLowerCase());
      });
      svg.append("text").attr("x", m.l + side / 2).attr("y", 12).attr("text-anchor", "middle").style("font-size", "11px").style("fill", css("--ink-3")).text("predicted →");
      svg.append("text").attr("x", 12).attr("y", m.t + side / 2).attr("text-anchor", "middle").attr("transform", `rotate(-90,12,${m.t + side / 2})`).style("font-size", "11px").style("fill", css("--ink-3")).text("true →");
    }, "All signals");
  }

  /* If the page is not visible (background tab, prerender, crawler), observers never fire:
     draw everything immediately, without animation. */
  function forceAll() {
    document.querySelectorAll(".reveal").forEach((el) => { el.classList.add("in"); el.querySelectorAll("[data-count]").forEach((c) => countUp(c, true)); });
    charts.forEach((c) => { if (!c.drawn) { c.drawn = true; c.draw(c.el, c.state, false); } });
  }
  window.__renderAllCharts = forceAll;   // used by automated checks / screenshots
  fetch("assets/data/site_data.json?v=3").then((r) => r.json()).then((D) => {
    drawAll(D);
    if (document.visibilityState === "hidden" || !("IntersectionObserver" in window)) forceAll();
  })
    .catch((e) => document.querySelectorAll(".chart").forEach((el) => (el.textContent = "Chart data failed to load.")));
})();
