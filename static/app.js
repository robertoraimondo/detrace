const state = {
  jobId: "",
  file: null,
  filename: "",
  sourceUrl: "",
  stems: [],
  players: [],
  mixPlaying: false,
  mixStartedAt: 0,
  jobs: [],
};

const els = {
  dropzone: document.querySelector("#dropzone"),
  fileInput: document.querySelector("#fileInput"),
  chooseBtn: document.querySelector("#chooseBtn"),
  sourcePlayer: document.querySelector("#sourcePlayer"),
  splash: document.querySelector("#splash"),
  startAppBtn: document.querySelector("#startAppBtn"),
  separateBtn: document.querySelector("#separateBtn"),
  exportBtn: document.querySelector("#exportBtn"),
  playMixBtn: document.querySelector("#playMixBtn"),
  stopMixBtn: document.querySelector("#stopMixBtn"),
  stems: document.querySelector("#stems"),
  uploadList: document.querySelector("#uploadList"),
  spectrumCanvas: document.querySelector("#spectrumCanvas"),
  clearUploadsBtn: document.querySelector("#clearUploadsBtn"),
  installToolsBtn: document.querySelector("#installToolsBtn"),
  log: document.querySelector("#log"),
  toolStatus: document.querySelector("#toolStatus"),
};

const visualizer = {
  context: null,
  analyser: null,
  data: null,
  sources: new WeakMap(),
  frame: 0,
};

function setAudioSource(audio, src) {
  audio.pause();
  audio.src = src;
  audio.load();
  audio.addEventListener("play", () => {
    ensureAudioNode(audio);
    startSpectrum();
  }, { once: true });
}

function log(message, type = "") {
  const item = document.createElement("li");
  item.textContent = message;
  if (type) item.className = type;
  els.log.prepend(item);
}

function setBusy(button, busy, label) {
  button.disabled = busy;
  if (label) button.textContent = label;
}

function updateTools(tools = {}) {
  for (const badge of els.toolStatus.querySelectorAll("[data-tool]")) {
    const name = badge.dataset.tool;
    const ready = Boolean(tools[name]);
    badge.classList.toggle("ready", ready);
    badge.classList.toggle("missing", !ready);
    badge.textContent = `${badge.textContent.split(" ")[0]} ${ready ? "ready" : "missing"}`;
  }
  els.installToolsBtn.hidden = toolsReady(tools);
}

async function getStatus() {
  const response = await fetch("/api/status");
  const data = await response.json();
  updateTools(data.tools);
  return data.tools;
}

function toolsReady(tools = {}) {
  return Boolean(tools.demucs && tools.ffmpeg && tools.codecs);
}

async function installTools() {
  setBusy(els.installToolsBtn, true, "Installing...");
  log("Installing missing audio tools. This can take a few minutes...");
  try {
    const response = await fetch("/api/install-tools", { method: "POST" });
    const data = await response.json();
    updateTools(data.tools);
    if (!response.ok) throw new Error(data.details || data.error || "Tool installation failed.");
    const installed = data.installed && data.installed.length ? data.installed.join(", ") : "nothing new";
    log(`Tool installation complete: ${installed}.`, "success");
    return data.tools;
  } finally {
    els.installToolsBtn.disabled = false;
    els.installToolsBtn.textContent = "Install Tools";
  }
}

async function ensureToolsReady() {
  const tools = await getStatus();
  if (toolsReady(tools)) return true;
  const installed = await installTools();
  return toolsReady(installed);
}

async function loadJobs() {
  const response = await fetch("/api/jobs");
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not load uploads.");
  state.jobs = data.jobs;
  updateTools(data.tools);
  renderJobs();
}

async function clearUploads() {
  if (!state.jobs.length) return;
  const confirmed = window.confirm("Clear all uploaded MP3s and analyzed tracks?");
  if (!confirmed) return;

  stopMix();
  const response = await fetch("/api/jobs", { method: "DELETE" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not clear uploads.");

  state.jobId = "";
  state.file = null;
  state.filename = "";
  state.sourceUrl = "";
  state.stems = [];
  state.players = [];
  state.jobs = [];
  setAudioSource(els.sourcePlayer, "");
  els.stems.innerHTML = "";
  els.separateBtn.disabled = true;
  els.exportBtn.disabled = true;
  els.playMixBtn.disabled = true;
  els.stopMixBtn.disabled = true;
  updateTools(data.tools);
  renderJobs();
  log("Uploaded MP3 list cleared.", "success");
}

function renderJobs() {
  els.uploadList.innerHTML = "";
  if (!state.jobs.length) {
    const empty = document.createElement("p");
    empty.className = "emptyUploads";
    empty.textContent = "No uploaded files yet.";
    els.uploadList.append(empty);
    return;
  }

  for (const job of state.jobs) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "uploadItem";
    button.classList.toggle("active", job.jobId === state.jobId);

    const title = document.createElement("span");
    title.className = "uploadName";
    title.textContent = job.filename;

    const meta = document.createElement("span");
    meta.className = "uploadMeta";
    meta.textContent = job.analyzed ? `${job.stems.length} tracks found` : "Not analyzed";

    button.append(title, meta);
    button.addEventListener("click", () => selectJob(job));
    els.uploadList.append(button);
  }
}

function loadJobIntoView(job) {
  stopMix();
  state.jobId = job.jobId;
  state.filename = job.filename;
  state.sourceUrl = job.sourceUrl;
  state.file = null;
  state.stems = (job.stems || []).map((stem) => ({ ...stem, active: true }));
  setAudioSource(els.sourcePlayer, job.sourceUrl);
  renderStems();
  syncPlayers();
  els.separateBtn.disabled = false;
  els.stopMixBtn.disabled = !state.stems.length;
  renderJobs();
}

async function selectJob(job) {
  try {
    const response = await fetch(`/api/jobs/${job.jobId}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load uploaded file.");
    updateTools(data.tools);
    loadJobIntoView(data.job);
    log(`Loaded ${data.job.filename}.`, "success");
  } catch (error) {
    log(error.message, "error");
  }
}

async function uploadFile(file) {
  state.file = file;
  state.filename = file.name;
  state.stems = [];
  state.players = [];
  els.stems.innerHTML = "";
  els.stems.setAttribute("aria-busy", "true");
  setAudioSource(els.sourcePlayer, URL.createObjectURL(file));
  els.separateBtn.disabled = true;
  els.exportBtn.disabled = true;
  els.playMixBtn.disabled = true;
  els.stopMixBtn.disabled = true;
  log(`Uploading ${file.name}...`);

  const response = await fetch("/api/upload", {
    method: "POST",
    headers: { "X-Filename": file.name },
    body: file,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Upload failed.");

  state.jobId = data.jobId;
  state.filename = data.filename;
  state.sourceUrl = data.sourceUrl;
  setAudioSource(els.sourcePlayer, data.sourceUrl);
  updateTools(data.tools);
  state.jobs = [{ ...data, stems: [], analyzed: false }, ...state.jobs.filter((job) => job.jobId !== data.jobId)];
  renderJobs();
  log("Upload complete. Analyzing instruments now...", "success");
  if (await ensureToolsReady()) {
    await separate();
  }
}

async function separate() {
  setBusy(els.separateBtn, true, "Analyzing...");
  els.exportBtn.disabled = true;
  els.playMixBtn.disabled = true;
  els.stopMixBtn.disabled = true;
  els.stems.innerHTML = "";
  els.stems.setAttribute("aria-busy", "true");
  log("Analyzing the MP3 and detecting separated instrument tracks. This can take a few minutes.");

  try {
    const response = await fetch("/api/separate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jobId: state.jobId, model: "htdemucs" }),
    });
    const data = await response.json();
    updateTools(data.tools);
    if (response.status === 424 && await ensureToolsReady()) {
      return separate();
    }
    if (!response.ok) throw new Error(data.details || data.error || "Separation failed.");

    state.stems = data.stems.map((stem) => ({ ...stem, active: true }));
    renderStems();
    els.exportBtn.disabled = false;
    els.playMixBtn.disabled = false;
    els.stopMixBtn.disabled = false;
    await loadJobs();
    log(`Found ${state.stems.length} tracks: ${state.stems.map((stem) => stem.name).join(", ")}.`, "success");
  } catch (error) {
    log(error.message, "error");
  } finally {
    els.separateBtn.disabled = false;
    els.separateBtn.textContent = "Analyze Again";
    els.stems.removeAttribute("aria-busy");
  }
}

function renderStems() {
  els.stems.innerHTML = "";
  state.players = [];

  for (const stem of state.stems) {
    const card = document.createElement("article");
    card.className = "stem";

    const header = document.createElement("div");
    header.className = "stemHeader";

    const name = document.createElement("p");
    name.className = "stemName";
    name.textContent = stem.name;

    const toggle = document.createElement("label");
    toggle.className = "toggle";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = stem.active;
    checkbox.addEventListener("change", () => {
      stem.active = checkbox.checked;
      syncPlayers();
    });
    toggle.append(checkbox, "Select");

    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";
    setAudioSource(audio, stem.url);

    header.append(name, toggle);
    card.append(header, audio);
    els.stems.append(card);
    state.players.push({ stem, audio });
  }
}

function syncPlayers() {
  const hasSelection = state.stems.some((stem) => stem.active);
  els.exportBtn.disabled = !hasSelection;
  els.playMixBtn.disabled = !hasSelection;
  els.stopMixBtn.disabled = !state.players.length;
  for (const { stem, audio } of state.players) {
    if (!stem.active && !audio.paused) {
      audio.pause();
    }
    if (stem.active && state.mixPlaying) {
      ensureAudioNode(audio);
      audio.currentTime = currentMixTime();
      audio.play().catch((error) => log(error.message, "error"));
    }
  }
}

async function playMix() {
  const activePlayers = state.players.filter(({ stem }) => stem.active);
  if (!activePlayers.length) return;
  stopMix();
  state.mixPlaying = true;
  state.mixStartedAt = performance.now();
  for (const { audio } of activePlayers) {
    ensureAudioNode(audio);
    audio.currentTime = 0;
  }
  startSpectrum();
  await Promise.all(activePlayers.map(({ audio }) => audio.play()));
}

function stopMix() {
  for (const { audio } of state.players) {
    audio.pause();
    audio.currentTime = 0;
  }
  state.mixPlaying = false;
  state.mixStartedAt = 0;
}

function currentMixTime() {
  if (!state.mixPlaying || !state.mixStartedAt) return 0;
  const elapsed = (performance.now() - state.mixStartedAt) / 1000;
  const durations = state.players
    .map(({ audio }) => audio.duration)
    .filter((duration) => Number.isFinite(duration) && duration > 0);
  if (!durations.length) return elapsed;
  return Math.min(elapsed, Math.max(...durations));
}

async function exportMix() {
  setBusy(els.exportBtn, true, "Exporting...");
  log("Exporting selected tracks to MP3...");

  try {
    const active = state.stems.filter((stem) => stem.active).map((stem) => stem.name);
    const response = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jobId: state.jobId, stems: active }),
    });
    const data = await response.json();
    updateTools(data.tools);
    if (response.status === 424 && await ensureToolsReady()) {
      return exportMix();
    }
    if (!response.ok) throw new Error(data.details || data.error || "Export failed.");

    await saveExport(data.url, data.filename);
    log("MP3 export downloaded.", "success");
  } catch (error) {
    log(error.message, "error");
  } finally {
    els.exportBtn.disabled = false;
    els.exportBtn.textContent = "Export MP3";
  }
}

async function saveExport(url, filename) {
  const response = await fetch(url);
  if (!response.ok) throw new Error("Could not download exported MP3.");
  const blob = await response.blob();

  if ("showSaveFilePicker" in window) {
    const handle = await window.showSaveFilePicker({
      suggestedName: filename,
      types: [
        {
          description: "MP3 audio",
          accept: { "audio/mpeg": [".mp3"] },
        },
      ],
    });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return;
  }

  downloadFile(URL.createObjectURL(blob), filename);
}

function downloadFile(url, filename) {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function ensureAudioNode(audio) {
  if (!visualizer.context) {
    const AudioApi = window.AudioContext || window.webkitAudioContext;
    visualizer.context = new AudioApi();
    visualizer.analyser = visualizer.context.createAnalyser();
    visualizer.analyser.fftSize = 256;
    visualizer.analyser.smoothingTimeConstant = 0.78;
    visualizer.data = new Uint8Array(visualizer.analyser.frequencyBinCount);
    visualizer.analyser.connect(visualizer.context.destination);
  }
  if (visualizer.context.state === "suspended") {
    visualizer.context.resume();
  }
  if (!visualizer.sources.has(audio)) {
    const source = visualizer.context.createMediaElementSource(audio);
    source.connect(visualizer.analyser);
    visualizer.sources.set(audio, source);
  }
}

function startSpectrum() {
  if (visualizer.frame) return;
  drawSpectrum();
}

function drawSpectrum() {
  const canvas = els.spectrumCanvas;
  const context = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const active = [els.sourcePlayer, ...state.players.map(({ audio }) => audio)].some((audio) => !audio.paused);

  context.clearRect(0, 0, width, height);
  context.fillStyle = "#11191d";
  context.fillRect(0, 0, width, height);

  if (visualizer.analyser && visualizer.data) {
    visualizer.analyser.getByteFrequencyData(visualizer.data);
    const bars = visualizer.data.length;
    const gap = 3;
    const barWidth = Math.max(3, (width - gap * bars) / bars);

    for (let index = 0; index < bars; index += 1) {
      const value = visualizer.data[index] / 255;
      const barHeight = Math.max(4, value * (height - 28));
      const x = index * (barWidth + gap);
      const y = height - barHeight;
      const hue = 178 + value * 45;
      context.fillStyle = `hsl(${hue}, 72%, ${42 + value * 28}%)`;
      context.fillRect(x, y, barWidth, barHeight);
    }
  }

  if (active) {
    visualizer.frame = requestAnimationFrame(drawSpectrum);
  } else {
    visualizer.frame = 0;
  }
}

els.chooseBtn.addEventListener("click", () => els.fileInput.click());
els.startAppBtn.addEventListener("click", () => {
  els.splash.classList.add("hidden");
});

els.fileInput.addEventListener("change", () => {
  const file = els.fileInput.files[0];
  if (file) uploadFile(file).catch((error) => log(error.message, "error"));
});

for (const event of ["dragenter", "dragover"]) {
  els.dropzone.addEventListener(event, (evt) => {
    evt.preventDefault();
    els.dropzone.classList.add("dragging");
  });
}

for (const event of ["dragleave", "drop"]) {
  els.dropzone.addEventListener(event, (evt) => {
    evt.preventDefault();
    els.dropzone.classList.remove("dragging");
  });
}

els.dropzone.addEventListener("drop", (evt) => {
  const file = evt.dataTransfer.files[0];
  if (file) uploadFile(file).catch((error) => log(error.message, "error"));
});

els.separateBtn.addEventListener("click", separate);
els.exportBtn.addEventListener("click", exportMix);
els.playMixBtn.addEventListener("click", playMix);
els.stopMixBtn.addEventListener("click", stopMix);
els.clearUploadsBtn.addEventListener("click", () => clearUploads().catch((error) => log(error.message, "error")));
els.installToolsBtn.addEventListener("click", () => installTools().catch((error) => log(error.message, "error")));

getStatus().catch(() => log("Could not read tool status.", "error"));
loadJobs().catch((error) => log(error.message, "error"));
