const sourceText = document.querySelector("#sourceText");
const outputText = document.querySelector("#outputText");
const destination = document.querySelector("#destination");
const runButton = document.querySelector("#runButton");
const sampleButton = document.querySelector("#sampleButton");
const clearButton = document.querySelector("#clearButton");
const copyOpenButton = document.querySelector("#copyOpenButton");
const copyButton = document.querySelector("#copyButton");
const setupStatus = document.querySelector("#setupStatus");
const riskBadge = document.querySelector("#riskBadge");
const categoryList = document.querySelector("#categoryList");
const reasonList = document.querySelector("#reasonList");
const engineStatus = document.querySelector("#engineStatus");

let lastPayload = null;

const sampleText = "Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 came in today. Mom Jennifer called from 512-555-0147 asking what vaccines he needs at this age.";

function setRisk(level) {
  riskBadge.className = `risk risk-${level || "idle"}`;
  riskBadge.textContent = level ? level[0].toUpperCase() + level.slice(1) : "Not run";
}

function renderCategories(categories) {
  categoryList.innerHTML = "";
  const entries = Object.entries(categories || {});
  if (!entries.length) {
    categoryList.textContent = "None";
    return;
  }
  for (const [name, count] of entries) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = `${name} ${count}`;
    categoryList.appendChild(chip);
  }
}

function renderReasons(reasons) {
  reasonList.innerHTML = "";
  if (!reasons || !reasons.length) {
    reasonList.textContent = "No blocking risk detected.";
    return;
  }
  for (const reason of reasons) {
    const item = document.createElement("div");
    item.textContent = reason;
    reasonList.appendChild(item);
  }
}

function renderEngine(payload) {
  if (!payload || !payload.engine) {
    engineStatus.textContent = "Engine: not run";
    engineStatus.className = "engine-status";
    return;
  }
  const label = payload.engine === "rules+openmed" ? "Rules + OpenMed" : "Local rules";
  const requested = payload.engine_requested && payload.engine_requested !== payload.engine
    ? ` (requested ${payload.engine_requested})`
    : "";
  engineStatus.textContent = `Engine: ${label}${requested}`;
  if (payload.engine_fallback_reason) {
    engineStatus.textContent += ` — ${payload.engine_fallback_reason}`;
  }
  engineStatus.className = payload.engine_fallback_reason
    ? "engine-status engine-status-warning"
    : "engine-status";
}

function setButtons(payload) {
  const allowed = Boolean(payload && payload.copy_allowed && payload.handoff);
  copyButton.disabled = !allowed;
  copyOpenButton.disabled = !allowed || !payload.handoff.open_url;
  if (payload && payload.handoff) {
    copyOpenButton.textContent = payload.handoff.action_label;
  } else {
    copyOpenButton.textContent = "Copy & Open";
  }
}

async function loadSetupStatus() {
  const response = await fetch("/api/setup/status", { cache: "no-store" });
  const payload = await response.json();
  setupStatus.textContent = payload.ner_model_ready ? "Local model ready" : "Rules ready; model setup pending";
  setupStatus.className = payload.ner_model_ready ? "status" : "status status-waiting";
}

async function runDecon() {
  runButton.disabled = true;
  runButton.textContent = "Running";
  try {
    const response = await fetch("/api/decon", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: sourceText.value,
        destination: destination.value,
      }),
    });
    const payload = await response.json();
    lastPayload = payload;
    outputText.value = payload.destination_prompt || "";
    setRisk(payload.risk_level);
    renderCategories(payload.removed_categories);
    renderReasons(payload.risk_reasons);
    renderEngine(payload);
    setButtons(payload);
  } finally {
    runButton.disabled = false;
    runButton.textContent = "Decontextualize";
  }
}

async function copyPrompt() {
  if (!lastPayload || !lastPayload.handoff || !lastPayload.copy_allowed) return false;
  await navigator.clipboard.writeText(lastPayload.handoff.copy_text);
  return true;
}

runButton.addEventListener("click", runDecon);

sampleButton.addEventListener("click", () => {
  sourceText.value = sampleText;
});

clearButton.addEventListener("click", () => {
  sourceText.value = "";
  outputText.value = "";
  lastPayload = null;
  setRisk(null);
  renderCategories({});
  renderReasons([]);
  renderEngine(null);
  setButtons(null);
});

copyButton.addEventListener("click", copyPrompt);

copyOpenButton.addEventListener("click", async () => {
  const copied = await copyPrompt();
  if (copied && lastPayload.handoff.open_url) {
    window.open(lastPayload.handoff.open_url, "_blank", "noopener,noreferrer");
  }
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

setRisk(null);
renderCategories({});
renderReasons([]);
renderEngine(null);
setButtons(null);
loadSetupStatus().catch(() => {
  setupStatus.textContent = "Setup status unavailable";
});
