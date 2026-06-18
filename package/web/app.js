const sourceText = document.querySelector("#sourceText");
const outputText = document.querySelector("#outputText");
const destination = document.querySelector("#destination");
const runButton = document.querySelector("#runButton");
const sampleButton = document.querySelector("#sampleButton");
const sampleSelect = document.querySelector("#sampleSelect");
const clearButton = document.querySelector("#clearButton");
const copyOpenButton = document.querySelector("#copyOpenButton");
const copyButton = document.querySelector("#copyButton");
const setupStatus = document.querySelector("#setupStatus");
const riskBadge = document.querySelector("#riskBadge");
const categoryList = document.querySelector("#categoryList");
const reasonList = document.querySelector("#reasonList");
const engineStatus = document.querySelector("#engineStatus");
const shutdownButton = document.querySelector("#shutdownButton");
const shutdownStatus = document.querySelector("#shutdownStatus");

let lastPayload = null;
let runProgressTimer = null;

const samples = {
  vaccine: "Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 came in today. Mom Jennifer called from 512-555-0147 asking what vaccines he needs at this age.",
  adhd: "Marvin returns for ADHD and anxiety follow-up. Mom says methylphenidate made him tearful and more anxious, so they stopped it 2 days ago. Starting guanfacine 1 mg qAM, may increase every 5 days to max 4 mg. Camp starts July 12; update requested before trip next Wednesday. Pharmacy Walgreens on Vernon.",
  asthma: "Portal from Alicia Rivera about Noah, DOB 6/2/2016: cough and wheeze after soccer, using albuterol every 4 hours, no fever, SpO2 97% at home. Needs asthma action plan for school nurse at Oak Hill Elementary.",
  renal: "Mr. Frank Patel, 78, CrCl 28 mL/min, on apixaban and amiodarone. Daughter Priya asks whether nitrofurantoin is safe for UTI after culture from Quest accession QST-492810.",
  pregnancy: "Samantha Lee is 10 weeks pregnant, called from 415-555-0192 asking if sertraline 50 mg should be continued. Prior postpartum depression; OB visit at Northside next Monday.",
  sibling: "Twin sibling note: Emma had strep last week, now Liam Chen MRN LC-9921 has sore throat and fever. Parent asks whether sibling exposure changes testing or antibiotics.",
  rare: "Aiden has recurrent fevers, aphthous ulcers, ferritin 920, ESR 74, and family asks about PFAPA versus periodic fever syndrome. Search current pediatric workup guidance.",
};

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

function setRunBusy(isBusy) {
  runButton.disabled = isBusy;
  runButton.textContent = isBusy ? "Running..." : "Decontextualize";
  runButton.setAttribute("aria-busy", isBusy ? "true" : "false");
}

function renderProgress(message) {
  lastPayload = null;
  outputText.value = message;
  setRisk(null);
  renderCategories({});
  renderReasons(["Running local privacy engine. Keep this tab open."]);
  renderEngine(null);
  setButtons(null);
}

function renderFailure(message, detail) {
  lastPayload = null;
  outputText.value = message;
  setRisk("high");
  renderCategories({});
  renderReasons([detail]);
  renderEngine(null);
  setButtons(null);
}

async function loadSetupStatus() {
  const response = await fetch("/api/setup/status", { cache: "no-store" });
  const payload = await response.json();
  setupStatus.textContent = payload.ner_model_ready ? "Local model ready" : "Rules ready; model setup pending";
  setupStatus.className = payload.ner_model_ready ? "status" : "status status-waiting";
}

async function runDecon() {
  if (!sourceText.value.trim()) {
    renderFailure("Paste clinical text before running decon.", "No source text entered.");
    return;
  }

  setRunBusy(true);
  renderProgress("Running local decon...\n\nThe first run after launch can take up to a minute while the local model loads.");
  runProgressTimer = window.setTimeout(() => {
    outputText.value = "Still running...\n\nThe first model-backed run can take 30-90 seconds on some Macs. Subsequent runs should be faster.";
    renderReasons(["Still loading the local OpenMed privacy model. Keep this tab open."]);
  }, 5000);

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch("/api/decon", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      signal: controller.signal,
      body: JSON.stringify({
        text: sourceText.value,
        destination: destination.value,
        engine: "rules+openmed",
      }),
    });
    if (!response.ok) {
      throw new Error(`Local server returned HTTP ${response.status}`);
    }
    const payload = await response.json();
    lastPayload = payload;
    outputText.value = payload.destination_prompt || "";
    setRisk(payload.risk_level);
    renderCategories(payload.removed_categories);
    renderReasons(payload.risk_reasons);
    renderEngine(payload);
    setButtons(payload);
  } catch (error) {
    const detail = error && error.name === "AbortError"
      ? "The local decon request timed out after 120 seconds. Reopen the app and try a shorter note."
      : `The local decon request failed. ${error && error.message ? error.message : "Reload the tab and try again."}`;
    renderFailure("Decon did not run.", detail);
  } finally {
    window.clearTimeout(timeout);
    window.clearTimeout(runProgressTimer);
    runProgressTimer = null;
    setRunBusy(false);
  }
}

async function copyPrompt() {
  if (!lastPayload || !lastPayload.handoff || !lastPayload.copy_allowed) return false;
  await navigator.clipboard.writeText(lastPayload.handoff.copy_text);
  return true;
}

runButton.addEventListener("click", runDecon);

sampleButton.addEventListener("click", () => {
  sourceText.value = samples[sampleSelect.value] || samples.vaccine;
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

shutdownButton.addEventListener("click", async () => {
  const shouldQuit = window.confirm("Quit Clinician Decon on this Mac?");
  if (!shouldQuit) return;

  shutdownButton.disabled = true;
  shutdownButton.textContent = "Quitting...";
  shutdownStatus.textContent = "Stopping local app.";
  try {
    await fetch("/api/shutdown", {
      method: "POST",
      cache: "no-store",
    });
  } catch (_) {
    // The server may close before the browser finishes reading the response.
  } finally {
    setupStatus.textContent = "Stopped";
    setupStatus.className = "status status-waiting";
    shutdownButton.textContent = "Quit";
    shutdownStatus.textContent = "Stopped. Close this window.";
  }
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").then((registration) => {
    registration.update().catch(() => {});
  }).catch(() => {});
}

setRisk(null);
renderCategories({});
renderReasons([]);
renderEngine(null);
setButtons(null);
loadSetupStatus().catch(() => {
  setupStatus.textContent = "Setup status unavailable";
});
