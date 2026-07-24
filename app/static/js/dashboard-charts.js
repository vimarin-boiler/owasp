(() => {
  "use strict";
  const source = document.getElementById("dashboardChartData");
  if (!source || typeof window.Chart === "undefined") return;
  let payload;
  try { payload = JSON.parse(source.dataset.chartPayload || "{}"); } catch (_) { return; }
  const css = getComputedStyle(document.documentElement);
  const primary = css.getPropertyValue("--ntt-primary").trim() || "#0072BC";
  const secondary = css.getPropertyValue("--ntt-secondary").trim() || "#00A7E1";
  const grid = "rgba(108,117,125,.14)";
  Chart.defaults.font.family = 'Inter, "Segoe UI", sans-serif';
  Chart.defaults.color = "#52677a";
  const legend = { labels: { usePointStyle: true, boxWidth: 8 } };
  const radar = document.getElementById("dashboardFunctionRadar");
  if (radar) new Chart(radar, { type: "radar", data: { labels: payload.functions.labels, datasets: [{ label: "Promedio", data: payload.functions.values, borderColor: primary, backgroundColor: "rgba(0,114,188,.16)", pointBackgroundColor: primary, borderWidth: 2 }] }, options: { maintainAspectRatio: false, plugins: { legend }, scales: { r: { min: 0, max: 3, ticks: { stepSize: 1, backdropColor: "transparent" }, grid: { color: grid }, angleLines: { color: grid } } } } });
  const practices = document.getElementById("dashboardPracticeBars");
  if (practices) new Chart(practices, { type: "bar", data: { labels: payload.practices.labels, datasets: [{ label: "Madurez promedio", data: payload.practices.values, backgroundColor: primary, borderRadius: 5 }] }, options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { min: 0, max: 3, ticks: { stepSize: .5 }, grid: { color: grid } }, y: { grid: { display: false } } } } });
  const progress = document.getElementById("dashboardProgressDistribution");
  if (progress) new Chart(progress, { type: "doughnut", data: { labels: payload.progress.labels, datasets: [{ data: payload.progress.values, backgroundColor: ["#dbe4eb", "#9bcce6", secondary, primary, "#198754"], borderWidth: 0 }] }, options: { maintainAspectRatio: false, cutout: "66%", plugins: { legend: { position: "right", ...legend } } } });
})();
