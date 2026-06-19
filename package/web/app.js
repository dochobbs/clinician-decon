const sourceText = document.querySelector("#sourceText");
const sourceMarkedWrap = document.querySelector("#sourceMarkedWrap");
const sourceMarked = document.querySelector("#sourceMarked");
const editSourceButton = document.querySelector("#editSourceButton");
const outputText = document.querySelector("#outputText");
const draftEmpty = document.querySelector("#draftEmpty");
const draftEmptyText = document.querySelector("#draftEmpty p");
const destination = document.querySelector("#destination");
const runButton = document.querySelector("#runButton");
const sampleButton = document.querySelector("#sampleButton");
const sampleSelect = document.querySelector("#sampleSelect");
const clearButton = document.querySelector("#clearButton");
const copyOpenButton = document.querySelector("#copyOpenButton");
const copyButton = document.querySelector("#copyButton");
const setupStatus = document.querySelector("#setupStatus");
const setupStatusText = document.querySelector("#setupStatusText");
const riskBadge = document.querySelector("#riskBadge");
const stateText = document.querySelector("#stateText");
const categoryList = document.querySelector("#categoryList");
const categoryLegend = document.querySelector("#categoryLegend");
const reasonList = document.querySelector("#reasonList");
const engineStatus = document.querySelector("#engineStatus");
const shutdownButton = document.querySelector("#shutdownButton");
const shutdownStatus = document.querySelector("#shutdownStatus");
const stage = document.querySelector(".stage");
const seam = document.querySelector(".seam");
const courier = document.querySelector("#courier");

let lastPayload = null;
let runProgressTimer = null;
let setupModelReady = null;

const IDLE_DRAFT_TEXT = "Your scrubbed draft will appear here for review.";
const REVIEW_CATEGORIES = new Set(["date", "location", "pharmacy", "school", "camp"]);
const PLACE_CATEGORIES = new Set(["location", "pharmacy", "school", "camp"]);

const samples = {
  vaccine: "Marcus Johnson DOB 3/15/2013 MRN LP-2024-08432 came in today. Mom Jennifer called from 512-555-0147 asking what vaccines he needs at this age.",
  adhd: "Marvin returns for ADHD and anxiety follow-up. Mom says methylphenidate made him tearful and more anxious, so they stopped it 2 days ago. Starting guanfacine 1 mg qAM, may increase every 5 days to max 4 mg. Camp starts July 12; update requested before trip next Wednesday. Pharmacy Walgreens on Vernon.",
  asthma: "Portal from Alicia Rivera about Noah, DOB 6/2/2016: cough and wheeze after soccer, using albuterol every 4 hours, no fever, SpO2 97% at home. Needs asthma action plan for school nurse at Oak Hill Elementary.",
  renal: "Mr. Frank Patel, 78, CrCl 28 mL/min, on apixaban and amiodarone. Daughter Priya asks whether nitrofurantoin is safe for UTI after culture from Quest accession QST-492810.",
  pregnancy: "Samantha Lee is 10 weeks pregnant, called from 415-555-0192 asking if sertraline 50 mg should be continued. Prior postpartum depression; OB visit at Northside next Monday.",
  sibling: "Twin sibling note: Emma had strep last week, now Liam Chen MRN LC-9921 has sore throat and fever. Parent asks whether sibling exposure changes testing or antibiotics.",
  rare: "Aiden has recurrent fevers, aphthous ulcers, ferritin 920, ESR 74, and family asks about PFAPA versus periodic fever syndrome. Search current pediatric workup guidance.",
};

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function categoryLabel(category) {
  return String(category).replace(/_/g, " ");
}

function setState(state) {
  const labels = {
    idle: "Nothing sent yet",
    reading: "Reading on this Mac...",
    ready: "Draft ready \u00b7 your review",
    copied: "Copied across",
    blocked: "Review before copying",
  };
  riskBadge.dataset.state = state;
  stateText.textContent = labels[state] || labels.idle;
}

function showDraftEmpty(message = IDLE_DRAFT_TEXT) {
  draftEmptyText.textContent = message;
  draftEmpty.hidden = false;
  outputText.hidden = true;
}

function showDraftText(text) {
  outputText.value = text || "";
  outputText.hidden = false;
  draftEmpty.hidden = true;
}

function backToEdit() {
  sourceMarkedWrap.hidden = true;
  sourceText.hidden = false;
}

function renderMarkedSource(spans) {
  const text = sourceText.value;
  const usableSpans = Array.isArray(spans)
    ? spans
      .filter((span) => Number.isInteger(span.start) && Number.isInteger(span.end))
      .filter((span) => span.start >= 0 && span.end > span.start && span.end <= text.length)
      .sort((a, b) => a.start - b.start || b.end - a.end)
    : [];

  let cursor = 0;
  let html = "";
  for (const span of usableSpans) {
    if (span.start < cursor) continue;
    html += escapeHtml(text.slice(cursor, span.start));
    const confidence = span.confidence === "review" ? "review" : "confident";
    const label = `${categoryLabel(span.category)}${confidence === "review" ? " - worth a look" : ""}`;
    html += `<mark class="${confidence}" title="${escapeHtml(label)}">${escapeHtml(text.slice(span.start, span.end))}</mark>`;
    cursor = span.end;
  }
  html += escapeHtml(text.slice(cursor));

  sourceMarked.innerHTML = html || escapeHtml(text);
  sourceText.hidden = true;
  sourceMarkedWrap.hidden = false;
}

function renderCategories(categories) {
  categoryList.innerHTML = "";
  const entries = Object.entries(categories || {});
  if (!entries.length) {
    categoryList.innerHTML = '<span class="empty-note">Nothing yet.</span>';
    categoryLegend.hidden = true;
    return 0;
  }

  let hasReview = false;
  for (const [name, count] of entries) {
    const chip = document.createElement("span");
    const isReview = REVIEW_CATEGORIES.has(name);
    hasReview = hasReview || isReview;
    chip.className = `chip${isReview ? " review" : ""}`;
    chip.textContent = `${categoryLabel(name)} ${count}`;
    categoryList.appendChild(chip);
  }
  categoryLegend.hidden = !hasReview && entries.length === 0;
  return entries.length;
}

function renderReviewPrompts(payload) {
  reasonList.innerHTML = "";
  if (!payload) {
    const item = document.createElement("li");
    item.className = "muted-check";
    item.textContent = "Run a reduction to see review prompts.";
    reasonList.appendChild(item);
    return;
  }

  const categories = new Set(Object.keys(payload.removed_categories || {}));
  const prompts = [
    "Initials, nicknames, and single first names often slip past automatic scrubbing - reread for them.",
    "A relationship can identify a patient with no name attached (\"mom is a nurse here,\" \"dad coaches at the high school\"). Reread for these.",
  ];

  if (categories.has("date")) {
    prompts.push("Loose dates near a small practice can re-identify even after names are gone - confirm each one in amber.");
  }
  if ([...categories].some((category) => PLACE_CATEGORIES.has(category))) {
    prompts.push("Specific places (clinic site, pharmacy, school) narrow the field fast in a small community.");
  }

  for (const prompt of prompts) {
    const item = document.createElement("li");
    item.textContent = prompt;
    reasonList.appendChild(item);
  }

  for (const reason of payload.risk_reasons || []) {
    const item = document.createElement("li");
    item.className = "risk-reason";
    item.textContent = reason;
    reasonList.appendChild(item);
  }
}

function renderEngine(payload, categoryCount = 0) {
  engineStatus.className = "engine-status";
  if (!payload || !payload.engine) {
    engineStatus.textContent = setupModelReady === false
      ? "Engine \u00b7 idle \u00b7 OpenMed setup pending"
      : "Engine \u00b7 idle";
    return;
  }

  const label = payload.engine === "rules+openmed" ? "Rules + OpenMed" : "Local rules";
  const requested = payload.engine_requested && payload.engine_requested !== payload.engine
    ? ` (requested ${payload.engine_requested})`
    : "";
  engineStatus.textContent = `Engine \u00b7 reduced locally \u00b7 ${categoryCount} categories \u00b7 ${label}${requested}`;
  if (payload.engine_fallback_reason) {
    engineStatus.textContent += ` - ${payload.engine_fallback_reason}`;
    engineStatus.className = "engine-status engine-status-warning";
  }
}

function setButtons(payload) {
  const allowed = Boolean(payload && payload.copy_allowed && outputText.value.trim());
  copyButton.disabled = !allowed;
  copyOpenButton.disabled = !allowed || !payload.handoff || !payload.handoff.open_url;
  copyOpenButton.textContent = "Copy across \u2192";
  copyButton.textContent = "Copy only";
}

function setRunBusy(isBusy) {
  runButton.disabled = isBusy;
  runButton.textContent = isBusy ? "Reading..." : "Reduce";
  runButton.setAttribute("aria-busy", isBusy ? "true" : "false");
}

function renderProgress() {
  lastPayload = null;
  setState("reading");
  showDraftEmpty("Reading on this Mac... The first run after launch can take up to a minute while the local model loads.");
  renderCategories({});
  renderReviewPrompts({
    removed_categories: {},
    risk_reasons: ["Running local privacy engine. Keep this window open."],
  });
  engineStatus.className = "engine-status";
  engineStatus.textContent = "Engine \u00b7 reading locally...";
  setButtons(null);
}

function renderFailure(message, detail) {
  lastPayload = null;
  setState("blocked");
  showDraftText(message);
  renderCategories({});
  renderReviewPrompts({
    removed_categories: {},
    risk_reasons: [detail],
  });
  engineStatus.className = "engine-status engine-status-warning";
  engineStatus.textContent = "Engine \u00b7 blocked";
  setButtons(null);
}

async function loadSetupStatus() {
  const response = await fetch("/api/setup/status", { cache: "no-store" });
  const payload = await response.json();
  setupModelReady = Boolean(payload.ner_model_ready);
  setupStatusText.textContent = "Running on this Mac";
  setupStatus.classList.toggle("setup-pending", !setupModelReady);
  setupStatus.title = setupModelReady
    ? "Local rules and OpenMed model are ready."
    : "Local rules are ready; OpenMed setup is pending.";
  if (!lastPayload) renderEngine(null);
}

async function runDecon() {
  const source = sourceText.value.trim();
  if (!source) {
    renderFailure("Paste clinical text before running decon.", "No source text entered.");
    sourceText.focus();
    return;
  }
  sourceText.value = source;

  setRunBusy(true);
  renderProgress();
  runProgressTimer = window.setTimeout(() => {
    showDraftEmpty("Still reading on this Mac... First model-backed runs can take 30-90 seconds on some Macs.");
    renderReviewPrompts({
      removed_categories: {},
      risk_reasons: ["Still loading the local OpenMed privacy model. Keep this window open."],
    });
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
        text: source,
        destination: destination.value,
        engine: "rules+openmed",
      }),
    });
    if (!response.ok) {
      throw new Error(`Local server returned HTTP ${response.status}`);
    }
    const payload = await response.json();
    if (payload.error) {
      renderFailure(payload.message || "Decon did not run.", (payload.risk_reasons || [payload.error]).join(" "));
      return;
    }

    lastPayload = payload;
    showDraftText(payload.destination_prompt || "");
    renderMarkedSource(payload.removed_spans);
    const categoryCount = renderCategories(payload.removed_categories);
    renderReviewPrompts(payload);
    renderEngine(payload, categoryCount);
    setButtons(payload);
    setState(payload.copy_allowed ? "ready" : "blocked");
  } catch (error) {
    const detail = error && error.name === "AbortError"
      ? "The local decon request timed out after 120 seconds. Reopen the app and try a shorter note."
      : `The local decon request failed. ${error && error.message ? error.message : "Reload the window and try again."}`;
    renderFailure("Decon did not run.", detail);
  } finally {
    window.clearTimeout(timeout);
    window.clearTimeout(runProgressTimer);
    runProgressTimer = null;
    setRunBusy(false);
  }
}

async function writeClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }
  outputText.focus();
  outputText.select();
  return document.execCommand("copy");
}

function flyCourier() {
  if (!stage || !seam || !courier) return;
  const stageRect = stage.getBoundingClientRect();
  const seamRect = seam.getBoundingClientRect();
  const startX = seamRect.left - stageRect.left - 120;
  const distance = stageRect.right - stageRect.left - startX - 150;
  courier.style.left = `${startX}px`;
  courier.style.setProperty("--cross-dist", `${distance}px`);
  courier.classList.remove("fly");
  void courier.offsetWidth;
  courier.classList.add("fly");
}

async function copyPrompt({ openExternal }) {
  if (!lastPayload || !lastPayload.copy_allowed || !outputText.value.trim()) return false;
  try {
    await writeClipboard(outputText.value);
  } catch (_) {
    renderReviewPrompts({
      removed_categories: lastPayload.removed_categories || {},
      risk_reasons: ["Clipboard access failed. Select the scrubbed draft and copy manually."],
    });
    return false;
  }

  setState("copied");
  engineStatus.className = "engine-status";
  engineStatus.textContent = "Engine \u00b7 copied to clipboard \u00b7 original never left";

  if (openExternal) {
    flyCourier();
    copyOpenButton.textContent = "Copied \u2713";
    window.setTimeout(() => {
      copyOpenButton.textContent = "Copy across \u2192";
    }, 1600);
    if (lastPayload.handoff && lastPayload.handoff.open_url) {
      window.open(lastPayload.handoff.open_url, "_blank", "noopener,noreferrer");
    }
  } else {
    copyButton.textContent = "Copied \u2713";
    window.setTimeout(() => {
      copyButton.textContent = "Copy only";
    }, 1400);
  }
  return true;
}

function resetAll({ clearSource = true } = {}) {
  if (clearSource) sourceText.value = "";
  backToEdit();
  showDraftEmpty();
  lastPayload = null;
  setState("idle");
  renderCategories({});
  renderReviewPrompts(null);
  renderEngine(null);
  setButtons(null);
}

runButton.addEventListener("click", runDecon);

sampleButton.addEventListener("click", () => {
  sourceText.value = samples[sampleSelect.value] || samples.vaccine;
  resetAll({ clearSource: false });
  sourceText.focus();
});

clearButton.addEventListener("click", () => {
  resetAll();
  sourceText.focus();
});

editSourceButton.addEventListener("click", () => {
  backToEdit();
  sourceText.focus();
});

destination.addEventListener("change", () => {
  if (lastPayload && sourceText.value.trim() && !runButton.disabled) {
    runDecon();
  }
});

copyButton.addEventListener("click", () => {
  copyPrompt({ openExternal: false });
});

copyOpenButton.addEventListener("click", () => {
  copyPrompt({ openExternal: true });
});

function requestNativeQuit() {
  const nativeHandler = window.webkit?.messageHandlers?.deconNative;
  if (!nativeHandler) return false;
  nativeHandler.postMessage({ action: "quit" });
  return true;
}

shutdownButton.addEventListener("click", async () => {
  const shouldQuit = window.confirm("Quit Decon on this Mac?");
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
    if (requestNativeQuit()) {
      shutdownStatus.textContent = "Closing app window.";
      return;
    }
    setupStatusText.textContent = "Stopped";
    setupStatus.classList.add("setup-pending");
    shutdownButton.textContent = "Quit";
    shutdownStatus.textContent = "Stopped. Close this window.";
  }
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").then((registration) => {
    registration.update().catch(() => {});
  }).catch(() => {});
}

resetAll();
loadSetupStatus().catch(() => {
  setupStatusText.textContent = "Running on this Mac";
  setupStatus.title = "Setup status unavailable.";
});
