(() => {
  "use strict";
  const source = document.getElementById("resultsChartData");
  if (!source) return;
  const containers = document.querySelectorAll(".chart-wrap");
  if (typeof window.Chart === "undefined") {
    containers.forEach((container) => {
      container.innerHTML = '<div class="chart-unavailable">No fue posible cargar el motor de gráficos.</div>';
    });
    return;
  }
  let payload;
  try {
    payload = JSON.parse(source.dataset.chartPayload || "{}");
  } catch (_) {
    return;
  }
  const css = getComputedStyle(document.documentElement);
  const primary = css.getPropertyValue("--ntt-primary").trim() || "#0072BC";
  const secondary = css.getPropertyValue("--ntt-secondary").trim() || "#00A7E1";
  const success = css.getPropertyValue("--ntt-success").trim() || "#198754";
  const warning = css.getPropertyValue("--ntt-warning").trim() || "#FFC107";
  const danger = css.getPropertyValue("--ntt-danger").trim() || "#DC3545";
  const muted = css.getPropertyValue("--ntt-muted").trim() || "#6C757D";
  const grid = "rgba(108, 117, 125, .16)";
  const text = "#52677a";
  Chart.defaults.font.family = 'Inter, "Segoe UI", sans-serif';
  Chart.defaults.color = text;
  const baseLegend = { labels: { usePointStyle: true, boxWidth: 8, padding: 18 } };

  const radar = document.getElementById("maturityRadar");
  if (radar && payload.radar) {
    new Chart(radar, {
      type: "radar",
      data: {
        labels: payload.radar.labels,
        datasets: [
          { label: "Madurez actual", data: payload.radar.current, borderColor: primary, backgroundColor: "rgba(0,114,188,.18)", pointBackgroundColor: primary, borderWidth: 2 },
          { label: "Nivel objetivo", data: payload.radar.target, borderColor: secondary, backgroundColor: "rgba(0,167,225,.05)", pointBackgroundColor: secondary, borderDash: [6,4], borderWidth: 2 }
        ]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: baseLegend }, scales: { r: { min: 0, max: 3, ticks: { stepSize: 1, backdropColor: "transparent" }, grid: { color: grid }, angleLines: { color: grid } } } }
    });
  }

  const practices = document.getElementById("practiceBars");
  if (practices && payload.practices) {
    new Chart(practices, {
      type: "bar",
      data: {
        labels: payload.practices.labels,
        datasets: [
          { label: "Actual", data: payload.practices.current, backgroundColor: primary, borderRadius: 5 },
          { label: "Objetivo", data: payload.practices.target, backgroundColor: "rgba(0,167,225,.38)", borderColor: secondary, borderWidth: 1, borderRadius: 5 }
        ]
      },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: baseLegend }, scales: { x: { min: 0, max: 3, ticks: { stepSize: .5 }, grid: { color: grid } }, y: { grid: { display: false }, ticks: { autoSkip: false } } } }
    });
  }

  const distribution = document.getElementById("responseDistribution");
  if (distribution && payload.distribution) {
    new Chart(distribution, {
      type: "doughnut",
      data: { labels: payload.distribution.labels, datasets: [{ data: payload.distribution.values, backgroundColor: [success, secondary, warning, danger, primary, muted, "#dbe4eb"], borderWidth: 0, hoverOffset: 5 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: "68%", plugins: { legend: { position: "right", ...baseLegend } } }
    });
  }

  const comparison = document.getElementById("overallComparison");
  if (comparison && payload.comparison) {
    new Chart(comparison, {
      type: "bar",
      data: { labels: payload.comparison.labels, datasets: [{ label: "Nivel", data: payload.comparison.values, backgroundColor: [primary, secondary], borderRadius: 8, maxBarThickness: 72 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 3, ticks: { stepSize: .5 }, grid: { color: grid } }, x: { grid: { display: false } } } }
    });
  }
})();
