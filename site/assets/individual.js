/* Wearable Exercise Physiology — "Individual responses" tab (D3 v7) */
(function () {
  "use strict";
  const reduce = /[?&]static/.test(location.search) || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const DUR = reduce ? 0 : 700;
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const fmt = (v, k = 1) => (v == null || !isFinite(v) ? "–" : (+v).toFixed(k));
  const signed = (v, k = 1) => (v == null || !isFinite(v) ? "–" : (v > 0 ? "+" : "") + (+v).toFixed(k));
  const isNarrow = () => window.innerWidth < 720;
  const points = (v) => (v == null ? "–" : signed(v, 0) + (Math.abs(v) === 1 ? " point" : " points"));
  const Z90 = 1.645;

  const SIG = {
    hr_mean: { label: "Heart rate", unit: "bpm", fmtv: (v) => signed(v, 1) + " bpm", tick: (d) => d },
    eda_log: { label: "EDA level", unit: "× baseline", fmtv: (v) => "×" + fmt(Math.pow(10, v), 2),
      tick: (d) => "×" + (+Math.pow(10, d).toPrecision(2)) },
    eda_scr_rate: { label: "SCR rate", unit: "per min", fmtv: (v) => signed(v, 1) + " /min", tick: (d) => d },
  };
  const CAT = { "Clear response": "--stress", "Unclear": "--unclear", "No meaningful response": "--ink-2" };
  const CAT_SHORT = { "Clear response": "clear response", "Unclear": "unclear", "No meaningful response": "no meaningful response" };
  const PROFILE = { "heart only": "--heart", "sweat only": "--sweat", "heart and sweat": "--both", "no clear response": "--unclear" };
  const ACSM = [[57, 64, "light"], [64, 77, "moderate"], [77, 96, "vigorous"], [96, 105, "near-max"]];

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

  /* ---------- theme (shared with the main page via localStorage) ---------- */
  const root = document.documentElement;
  try { const s = localStorage.getItem("theme"); if (s) root.setAttribute("data-theme", s); } catch (e) {}
  document.getElementById("themeBtn").addEventListener("click", () => {
    const dark = root.getAttribute("data-theme") === "dark" ||
      (!root.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
    const next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (e) {}
    redrawAll();
  });

  /* ---------- chart registry ---------- */
  const charts = [];
  function register(id, draw, initial) {
    const el = document.getElementById(id);
    if (!el) return;
    const c = { el, draw, state: initial };
    charts.push(c);
    draw(el, c.state, true);
    const ctl = document.querySelector(`[data-controls="${id}"]`);
    if (ctl) ctl.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      ctl.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      c.state = b.dataset.value; c.draw(c.el, c.state, true);
    }));
  }
  function redrawAll() { charts.forEach((c) => c.draw(c.el, c.state, false)); renderCard(current); }
  let rt; window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(redrawAll, 200); });

  function frame(el, height, m) {
    el.innerHTML = "";
    const W = Math.max(300, el.clientWidth), H = height;
    const svg = d3.select(el).append("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img");
    return { svg, W, H, iw: W - m.l - m.r, ih: H - m.t - m.b, g: svg.append("g").attr("transform", `translate(${m.l},${m.t})`) };
  }
  d3.selection.prototype.maybe = function (anim, delay) {
    return anim && !reduce ? this.transition().duration(DUR).delay(delay || 0) : this;
  };

  let D, byId = {}, current = null;

  function drawAll() {
    const P = D.profiles, N = D.noise;

    /* 1 · Forest plot of individual responses */
    register("chart-forest", (el, sig, anim) => {
      const s = SIG[sig], nz = N[sig];
      const data = P.filter((p) => p[sig + "_response"] != null)
        .sort((a, b) => b[sig + "_response"] - a[sig + "_response"]);
      const m = { t: 22, r: 14, b: 36, l: 40 };
      const f = frame(el, data.length * 17 + m.t + m.b, m);
      const lo = d3.min(data, (d) => d[sig + "_ci90_low"]), hi = d3.max(data, (d) => d[sig + "_ci90_high"]);
      const x = d3.scaleLinear([Math.min(lo, 0), Math.max(hi, 0)], [0, f.iw]).nice();
      const y = d3.scaleBand(data.map((d) => d.id), [0, f.ih]).padding(0.3);
      f.g.append("g").attr("class", "grid").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(6).tickSize(-f.ih).tickFormat(""));
      f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(6).tickFormat(s.tick))
        .append("text").attr("x", f.iw).attr("y", 32).attr("text-anchor", "end").style("fill", css("--ink-3")).text(`TMCT − seated baseline (${s.unit})`);
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickSize(0)).select(".domain").remove();
      f.g.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", 0).attr("y2", f.ih).attr("stroke", css("--ink")).attr("stroke-width", 1);
      f.g.append("line").attr("x1", x(nz.swc)).attr("x2", x(nz.swc)).attr("y1", -6).attr("y2", f.ih).attr("stroke", css("--ink-2")).attr("stroke-dasharray", "4 3");
      f.g.append("text").attr("x", x(nz.swc) + 4).attr("y", -9).style("font-size", "11px").style("fill", css("--ink-3")).text("smallest worthwhile change");
      data.forEach((d, i) => {
        const cy = y(d.id) + y.bandwidth() / 2, c = css(CAT[d[sig + "_category"]]);
        f.g.append("line").attr("y1", cy).attr("y2", cy).attr("x1", x(0)).attr("x2", x(0)).attr("stroke", c).attr("stroke-width", 3).attr("stroke-linecap", "round")
          .maybe(anim, i * 12).attr("x1", x(d[sig + "_ci90_low"])).attr("x2", x(d[sig + "_ci90_high"]));
        f.g.append("circle").attr("cy", cy).attr("cx", x(0)).attr("r", 4.5).attr("fill", c).attr("stroke", css("--surface")).attr("stroke-width", 1.5)
          .maybe(anim, i * 12).attr("cx", x(d[sig + "_response"]));
        f.g.append("rect").attr("x", -m.l).attr("width", f.iw + m.l).attr("y", y(d.id) - 2).attr("height", y.bandwidth() + 4).attr("fill", "transparent").style("cursor", "pointer")
          .on("mousemove", (e) => showTip(e, `<b>${d.id}</b> · ${CAT_SHORT[d[sig + "_category"]]}<br>${s.label}: <b>${s.fmtv(d[sig + "_response"])}</b><br>90% interval ${s.fmtv(d[sig + "_ci90_low"])} to ${s.fmtv(d[sig + "_ci90_high"])}`))
          .on("mouseleave", hideTip).on("click", () => openCard(d.id));
      });
      const cnt = d3.rollup(data, (v) => v.length, (d) => d[sig + "_category"]);
      document.getElementById("note-forest").textContent =
        `${s.label}: ${cnt.get("Clear response") || 0} clear, ${cnt.get("Unclear") || 0} unclear, ${cnt.get("No meaningful response") || 0} no meaningful response (n = ${data.length}). ` +
        `Typical error ${s.fmtv(nz.te).replace("+", "")}, smallest worthwhile change ${s.fmtv(nz.swc).replace("+", "")}. Click a row to open that person's card.`;
    }, "hr_mean");

    /* 2 · Repeats needed */
    register("chart-repeats", (el, teKey, anim) => {
      const ks = d3.range(1, 21);
      const series = Object.keys(SIG).map((sig, i) => ({
        sig, color: [css("--accent"), css("--ink-2"), css("--ink-3")][i], dash: ["0", "6 4", "2 3"][i],
        values: ks.map((k) => ({ k, v: Z90 * Math.SQRT2 * N[sig][teKey] / Math.sqrt(k) / N[sig].swc })),
      }));
      const m = { t: 14, r: isNarrow() ? 70 : 110, b: 40, l: 44 };
      const f = frame(el, 300, m);
      const x = d3.scaleLinear([1, 20], [0, f.iw]);
      const y = d3.scaleLinear([0, Math.min(8, d3.max(series, (s) => s.values[0].v) * 1.05)], [f.ih, 0]).nice();
      f.g.append("g").attr("class", "grid").call(d3.axisLeft(y).ticks(5).tickSize(-f.iw).tickFormat(""));
      f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).tickValues([1, 2, 4, 6, 8, 10, 14, 20]))
        .append("text").attr("x", f.iw).attr("y", 34).attr("text-anchor", "end").style("fill", css("--ink-3")).text("repeated stress tests averaged");
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(5).tickFormat((d) => d + "×"));
      f.g.append("line").attr("x1", 0).attr("x2", f.iw).attr("y1", y(1)).attr("y2", y(1)).attr("stroke", css("--ink")).attr("stroke-width", 1.2);
      f.g.append("text").attr("x", 4).attr("y", y(1) + 15).style("font-size", "11px").style("fill", css("--ink-3")).text("noise = smallest worthwhile change");
      // end labels, nudged apart so they never overlap
      const ends = series.map((s) => ({ s, y: y(Math.min(s.values[s.values.length - 1].v, y.domain()[1])) })).sort((a, b) => a.y - b.y);
      ends.forEach((e, i) => { if (i && e.y - ends[i - 1].y < 15) e.y = ends[i - 1].y + 15; });
      const labelY = new Map(ends.map((e) => [e.s.sig, e.y]));
      const line = d3.line().x((d) => x(d.k)).y((d) => y(Math.min(d.v, y.domain()[1])));
      series.forEach((s, i) => {
        const p = f.g.append("path").datum(s.values).attr("fill", "none").attr("stroke", s.color).attr("stroke-width", 2.4).attr("stroke-dasharray", s.dash).attr("d", line);
        const kNeed = Math.ceil(Math.pow(Z90 * Math.SQRT2 * N[s.sig][teKey] / N[s.sig].swc, 2));
        f.g.append("text").attr("x", f.iw + 6).attr("y", labelY.get(s.sig)).attr("dy", "0.35em").style("font-size", "12px").style("fill", css("--ink-2"))
          .text(`${SIG[s.sig].label}: ${kNeed > 20 ? ">20" : kNeed}`);
        if (kNeed <= 20) f.g.append("circle").attr("cx", x(kNeed)).attr("cy", y(Z90 * Math.SQRT2 * N[s.sig][teKey] / Math.sqrt(kNeed) / N[s.sig].swc)).attr("r", 4.5)
          .attr("fill", s.color).attr("stroke", css("--surface")).attr("stroke-width", 1.5);
        if (anim && !reduce) {
          const L = p.node().getTotalLength();
          p.attr("stroke-dasharray", `${L} ${L}`).attr("stroke-dashoffset", L).transition().duration(DUR + 300).delay(i * 120)
            .attr("stroke-dashoffset", 0).on("end", function () { d3.select(this).attr("stroke-dasharray", s.dash); });
        }
      });
    }, "te");

    /* 3 · Response channels */
    const legend = document.getElementById("legend-channels");
    legend.innerHTML = Object.entries(PROFILE).map(([k, v]) =>
      `<span><i style="background:var(${v})"></i>${k} (n = ${P.filter((p) => p.profile === k).length})</span>`).join("");
    register("chart-channels", (el, _s, anim) => {
      const data = P.filter((p) => p.profile);
      const m = { t: 12, r: 16, b: 42, l: 56 };
      const f = frame(el, isNarrow() ? 320 : 400, m);
      const x = d3.scaleLinear(d3.extent(data, (d) => d.hr_mean_response), [0, f.iw]).nice();
      const y = d3.scaleLog([0.5, 7], [f.ih, 0]);
      const yt = [0.5, 0.75, 1, 1.5, 2, 3, 4, 6];
      f.g.append("g").attr("class", "grid").call(d3.axisLeft(y).tickValues(yt).tickSize(-f.iw).tickFormat(""));
      f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).ticks(6))
        .append("text").attr("x", f.iw).attr("y", 36).attr("text-anchor", "end").style("fill", css("--ink-3")).text("HR response (bpm)");
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickValues(yt).tickFormat((d) => "×" + d))
        .append("text").attr("transform", "rotate(-90)").attr("x", 0).attr("y", -44).attr("text-anchor", "end").style("fill", css("--ink-3")).text("EDA level response");
      f.g.append("line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", 0).attr("y2", f.ih).attr("stroke", css("--ink"));
      f.g.append("line").attr("x1", 0).attr("x2", f.iw).attr("y1", y(1)).attr("y2", y(1)).attr("stroke", css("--ink"));
      f.g.append("line").attr("x1", x(N.hr_mean.swc)).attr("x2", x(N.hr_mean.swc)).attr("y1", 0).attr("y2", f.ih).attr("stroke", css("--ink-2")).attr("stroke-dasharray", "4 3");
      const ey = y(Math.pow(10, N.eda_log.swc));
      f.g.append("line").attr("x1", 0).attr("x2", f.iw).attr("y1", ey).attr("y2", ey).attr("stroke", css("--ink-2")).attr("stroke-dasharray", "4 3");
      data.forEach((d, i) => {
        f.g.append("circle").attr("cx", x(d.hr_mean_response)).attr("cy", y(d.eda_ratio)).attr("r", anim && !reduce ? 0 : 6.5)
          .attr("fill", css(PROFILE[d.profile])).attr("stroke", css("--surface")).attr("stroke-width", 1.5).style("cursor", "pointer")
          .on("mousemove", (e) => showTip(e, `<b>${d.id}</b> · ${d.profile}<br>HR ${signed(d.hr_mean_response)} bpm (${CAT_SHORT[d.hr_mean_category]})<br>EDA ×${fmt(d.eda_ratio, 2)} (${CAT_SHORT[d.eda_log_category]})<br>Self-report ${points(d.selfreport_change)}`))
          .on("mouseleave", hideTip).on("click", () => openCard(d.id))
          .maybe(anim, i * 18).attr("r", 6.5);
      });
      const rho = spearman(data.map((d) => d.hr_mean_response), data.map((d) => d.eda_log_response));
      document.getElementById("note-channels").textContent =
        `Spearman ρ = ${fmt(rho, 2)} (n = ${data.length}). Of the people with a clear response on at least one signal, only ` +
        `${data.filter((d) => d.profile === "heart and sweat").length} respond on both.`;
    });

    /* 4 · Relative intensity */
    register("chart-intensity", (el, _s, anim) => {
      const data = P.filter((p) => p.hr_valid_aerobic != null && p.age != null)
        .sort((a, b) => {
          const na = a.pct_hrmax_peak == null, nb = b.pct_hrmax_peak == null;
          if (na || nb) return na === nb ? (a.pct_hrmax_moderate ?? 0) - (b.pct_hrmax_moderate ?? 0) : na - nb;
          return a.pct_hrmax_peak - b.pct_hrmax_peak;
        });
      const m = { t: 10, r: isNarrow() ? 8 : 70, b: 46, l: 44 };
      const f = frame(el, 360, m);
      const x = d3.scaleBand(data.map((d) => d.id), [0, f.iw]).padding(0.2);
      const y = d3.scaleLinear([30, 100], [f.ih, 0]);
      ACSM.forEach(([lo, hi, lab], i) => {
        f.g.append("rect").attr("x", 0).attr("width", f.iw).attr("y", y(Math.min(hi, 100))).attr("height", y(lo) - y(Math.min(hi, 100)))
          .attr("fill", css("--aerobic")).attr("opacity", 0.05 + 0.04 * i);
        if (!isNarrow()) f.g.append("text").attr("x", f.iw + 6).attr("y", (y(lo) + y(Math.min(hi, 100))) / 2).attr("dy", "0.35em")
          .style("font-size", "11px").style("fill", css("--ink-3")).text(lab);
      });
      f.g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(7).tickFormat((d) => d + "%"));
      const ax = f.g.append("g").attr("class", "axis").attr("transform", `translate(0,${f.ih})`).call(d3.axisBottom(x).tickSize(0));
      ax.select(".domain").remove();
      ax.selectAll("text").attr("transform", "rotate(-90)").attr("text-anchor", "end").attr("dx", "-0.6em").attr("dy", "-0.5em").style("font-size", "10px");
      if (x.step() < 13) ax.selectAll("text").remove();   // too narrow for 30 labels: rely on the tooltip
      data.forEach((d, i) => {
        const cx = x(d.id) + x.bandwidth() / 2;
        if (d.pct_hrmax_moderate != null && d.pct_hrmax_peak != null)
          f.g.append("line").attr("x1", cx).attr("x2", cx).attr("y1", y(d.pct_hrmax_moderate)).attr("y2", y(d.pct_hrmax_moderate))
            .attr("stroke", css("--rule")).attr("stroke-width", 2).maybe(anim, i * 15).attr("y2", y(d.pct_hrmax_peak));
        if (d.pct_hrmax_moderate != null)
          f.g.append("circle").attr("cx", cx).attr("cy", y(d.pct_hrmax_moderate)).attr("r", 4).attr("fill", css("--unclear"));
        if (d.pct_hrmax_peak != null)
          f.g.append("circle").attr("cx", cx).attr("cy", y(d.pct_hrmax_moderate ?? d.pct_hrmax_peak)).attr("r", 6)
            .attr("fill", d.peak_reliable ? css("--aerobic") : css("--surface")).attr("stroke", d.peak_reliable ? css("--surface") : css("--aerobic"))
            .attr("stroke-width", d.peak_reliable ? 1.5 : 2).maybe(anim, i * 15).attr("cy", y(d.pct_hrmax_peak));
        f.g.append("rect").attr("x", x(d.id)).attr("width", x.bandwidth()).attr("y", 0).attr("height", f.ih).attr("fill", "transparent").style("cursor", "pointer")
          .on("mousemove", (e) => showTip(e, `<b>${d.id}</b> · final stage ${stageLabel(d.peak_stage)}<br>Moderate stages: ${pct(d.pct_hrmax_moderate)}<br>Final stage: ${pct(d.pct_hrmax_peak)}${d.acsm_peak ? " (" + d.acsm_peak + ")" : ""}<br>${peakReason(d)}`))
          .on("mouseleave", hideTip).on("click", () => openCard(d.id));
      });
      const rel = data.filter((d) => d.peak_reliable).map((d) => d.pct_hrmax_peak);
      document.getElementById("note-intensity").textContent =
        `${rel.length} of ${data.length} participants with age and an aerobic session have a reliable final-stage HR: ` +
        `${fmt(d3.min(rel), 0)}–${fmt(d3.max(rel), 0)}% of predicted HRmax (median ${fmt(d3.median(rel), 0)}%). ` +
        `Participants on the right had no valid final-stage HR.`;
    });

    /* 5 · Profile cards */
    const sel = document.getElementById("pick");
    sel.innerHTML = P.map((p) => `<option value="${p.id}">${p.id}${p.profile ? " · " + p.profile : ""}</option>`).join("");
    sel.addEventListener("change", () => renderCard(sel.value));
    document.querySelectorAll("#examples button").forEach((b) => b.addEventListener("click", () => renderCard(b.dataset.id)));
    const fromHash = location.hash.match(/^#p=(\w+)/);
    renderCard(fromHash && byId[fromHash[1]] ? fromHash[1] : "S04");
  }

  /* ---------- profile card ---------- */
  const pct = (v) => (v == null ? "–" : fmt(v, 0) + "% HRmax");
  const stageLabel = (s) => (s ? s.replace("rpm_", "").replace("_partial", " (partial)").replace("_", "–") + " rpm" : "–");
  function peakReason(d) {
    if (d.pct_hrmax_peak == null) return d.age == null ? "age not recorded" : "no valid final-stage HR";
    if (d.peak_reliable) return `reliable (${d.peak_valid_windows} valid windows)`;
    if (!d.peak_enough_data) return `unreliable: only ${d.peak_valid_windows} valid window${d.peak_valid_windows === 1 ? "" : "s"}`;
    return "unreliable: lower than the moderate stages";
  }
  function openCard(id) {
    renderCard(id);
    document.getElementById("cards").scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
  }
  function miniBar(sig, d) {
    const N = D.noise[sig], P = D.profiles;
    const lo = d3.min(P, (p) => p[sig + "_ci90_low"]), hi = d3.max(P, (p) => p[sig + "_ci90_high"]);
    const W = 300, H = 26, x = d3.scaleLinear([Math.min(lo, 0), Math.max(hi, 0)], [6, W - 6]);
    const r = d[sig + "_response"];
    if (r == null) return `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true"></svg>`;
    const c = css(CAT[d[sig + "_category"]]);
    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">
      <line x1="${x(0)}" x2="${x(0)}" y1="2" y2="${H - 2}" stroke="${css("--ink")}" stroke-width="1"/>
      <line x1="${x(N.swc)}" x2="${x(N.swc)}" y1="2" y2="${H - 2}" stroke="${css("--ink-2")}" stroke-dasharray="3 3"/>
      <line x1="${x(d[sig + "_ci90_low"])}" x2="${x(d[sig + "_ci90_high"])}" y1="${H / 2}" y2="${H / 2}" stroke="${c}" stroke-width="5" stroke-linecap="round"/>
      <circle cx="${x(r)}" cy="${H / 2}" r="6" fill="${c}" stroke="${css("--surface")}" stroke-width="1.5"/></svg>`;
  }
  const pill = (cat) => cat ? `<span class="pill"><i style="background:var(${CAT[cat]})"></i>${CAT_SHORT[cat]}</span>` : `<span class="pill">no data</span>`;
  const share = (v) => (v == null ? "no session" : Math.round(v * 100) + "%");

  function advice(d) {
    const out = [], N = D.noise;
    const unclear = Object.keys(SIG).filter((s) => d[s + "_category"] === "Unclear");
    if (d.profile === "heart only") out.push("Responded through the heart, not the sweat glands: a skin-conductance-only monitor would have missed this response.");
    if (d.profile === "sweat only") out.push("Responded through the sweat glands, not the heart: a heart-rate-only monitor would have missed this response.");
    if (d.profile === "heart and sweat") out.push("Clear response on both channels in this session.");
    if (d.profile === "no clear response") out.push("No clear response in this session. That does not mean this person is not reactive: one short test cannot tell.");
    if (unclear.length) out.push(`Unclear on ${unclear.map((s) => SIG[s].label.toLowerCase()).join(" and ")}: about ${unclear.map((s) => N[s].repeats_needed).sort((a, b) => b - a)[0]} repeated tests would be needed before labelling.`);
    const anyClear = Object.keys(SIG).some((s) => d[s + "_category"] === "Clear response");
    if (anyClear && d.selfreport_change != null && d.selfreport_change <= 0) out.push("Reported no increase in stress despite a clear physiological response: ask and measure, one does not replace the other.");
    if (d.movement_change != null && d.movement_change < 0 && anyClear) out.push("The wrist was stiller than at rest during the task, so the response is not a movement artefact.");
    if (d.hr_valid_aerobic == null) out.push("No aerobic cycling session recorded.");
    else if (d.peak_reliable) out.push(`The final cycling stage reached ${fmt(d.pct_hrmax_peak, 0)}% of age-predicted HRmax (${d.acsm_peak}). Age-predicted HRmax carries about ±10 bpm of individual error.`);
    else out.push(`Final-stage wrist HR is not usable (${peakReason(d)}): verify intensity with a chest strap or RPE.`);
    return out;
  }

  function renderCard(id) {
    if (!id || !byId[id]) return;
    current = id;
    const d = byId[id];
    document.getElementById("pick").value = id;
    document.querySelectorAll("#examples button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.id === id));
    try { history.replaceState(null, "", "#p=" + id); } catch (e) {}
    const sex = { m: "man", f: "woman" }[d.sex] || "sex not recorded";
    const age = d.age == null ? "age not recorded" : `${d.age} y`;
    const active = d.active ? `physically active: ${d.active.toLowerCase()}` : "activity not recorded";
    const rows = Object.keys(SIG).map((s) => `
      <div class="sigrow"><div class="lab">${SIG[s].label}</div>${miniBar(s, d)}
        <div class="val">${d[s + "_response"] == null ? "no valid data" : SIG[s].fmtv(d[s + "_response"])} ${pill(d[s + "_category"])}</div></div>`).join("");
    document.getElementById("pcard").innerHTML = `
      <div class="pcard-head"><b>${d.id}</b><span>${sex} · ${age} · cohort ${d.cohort} · ${active}</span>
        ${d.profile ? `<span class="pill"><i style="background:var(${PROFILE[d.profile]})"></i>${d.profile}</span>` : ""}</div>
      <div class="pcard">
        <div><h4>Stress session · task vs seated baseline</h4>${rows}
          <dl class="kv" style="margin-top:12px">
            <dt>Self-reported stress</dt><dd>${d.selfreport_change == null ? "–" : points(d.selfreport_change) + " on the rating scale"}</dd>
            <dt>Wrist movement</dt><dd>${d.movement_change == null ? "–" : d.movement_change < 0 ? "stiller than at rest" : "slightly more than at rest"}</dd>
          </dl></div>
        <div><h4>Exercise · relative intensity</h4>
          <dl class="kv">
            <dt>Moderate stages</dt><dd>${pct(d.pct_hrmax_moderate)}</dd>
            <dt>Final stage</dt><dd>${pct(d.pct_hrmax_peak)}${d.acsm_peak && d.peak_reliable ? " · " + d.acsm_peak : ""} <span class="muted">(${stageLabel(d.peak_stage)})</span></dd>
            <dt>Reliability</dt><dd>${peakReason(d)}</dd>
            <dt>Predicted HRmax</dt><dd>${d.hrmax_pred == null ? "–" : fmt(d.hrmax_pred, 0) + " bpm (208 − 0.7 × age)"}</dd>
          </dl>
          <h4 style="margin-top:16px">Usable wrist heart rate</h4>
          <dl class="kv">
            <dt>Stress day</dt><dd>${share(d.hr_valid_stress)} of windows</dd>
            <dt>Aerobic day</dt><dd>${share(d.hr_valid_aerobic)} of windows</dd>
            <dt>Anaerobic day</dt><dd>${share(d.hr_valid_anaerobic)} of windows</dd>
          </dl></div>
      </div>
      <ul class="advice">${advice(d).map((a) => `<li>${a}</li>`).join("")}</ul>`;
  }

  function spearman(a, b) {
    const rank = (v) => { const s = v.map((x, i) => [x, i]).sort((p, q) => p[0] - q[0]), r = Array(v.length);
      s.forEach(([, i], k) => (r[i] = k)); return r; };
    const ra = rank(a), rb = rank(b), ma = d3.mean(ra), mb = d3.mean(rb);
    let num = 0, da = 0, db = 0;
    ra.forEach((x, i) => { num += (x - ma) * (rb[i] - mb); da += (x - ma) ** 2; db += (rb[i] - mb) ** 2; });
    return num / Math.sqrt(da * db);
  }

  fetch("assets/data/individual_data.json?v=1").then((r) => r.json()).then((data) => {
    D = data;
    D.profiles.forEach((p) => (byId[p.id] = p));
    drawAll();
  }).catch(() => document.querySelectorAll(".chart, #pcard").forEach((el) => (el.textContent = "Data failed to load.")));
})();
