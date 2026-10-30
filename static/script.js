const runBtn = document.getElementById("run-btn");
const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const errorEl = document.getElementById("error");
const errorTitle = document.getElementById("error-title");
const chartSection = document.getElementById("chart-section");
const chartEl = document.getElementById("chart");
const filesSection = document.getElementById("files-section");
const filesEl = document.getElementById("files");

function showError(text) {
  const has = Boolean(text && text.trim());
  errorEl.textContent = has ? text : "";
  errorEl.hidden = !has;
  errorTitle.hidden = !has;
}

function showFiles(files) {
  filesEl.innerHTML = "";
  const hasChart = files.includes("analysis_charts.png");

  chartSection.hidden = !hasChart;
  if (hasChart) {
    // Cache-bust so a fresh run always shows the new chart.
    chartEl.src = "/outputs/analysis_charts.png?t=" + Date.now();
  }

  files.forEach((name) => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = "/outputs/" + encodeURIComponent(name);
    a.textContent = name;
    a.download = name;
    li.appendChild(a);
    filesEl.appendChild(li);
  });
  filesSection.hidden = files.length === 0;
}

async function runAnalysis() {
  runBtn.disabled = true;
  statusEl.textContent = "Running... scraping all pages can take a little while.";
  showError("");

  try {
    const res = await fetch("/api/run", { method: "POST" });
    const data = await res.json();
    outputEl.textContent = data.output || "(no output)";
    // showError(data.error);
    showFiles(data.files || []);
    // statusEl.textContent = data.ok ? "Done." : "Finished with errors.";
  } catch (err) {
    statusEl.textContent = "Request failed.";
    showError(String(err));
  } finally {
    runBtn.disabled = false;
  }
}

runBtn.addEventListener("click", runAnalysis);
