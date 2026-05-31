const LEVEL_LABELS = {
  1: "Soft setup",
  2: "Calm redirect",
  3: "Controlled strike",
  4: "Psych pressure",
  5: "Checkmate",
};

const IMAGE_EXTENSIONS = new Set(["png", "jpg", "jpeg", "webp", "heic", "gif"]);

const $ = (sel) => document.querySelector(sel);

const dropzone = $("#dropzone");
const fileInput = $("#file-input");
const previews = $("#previews");
const transcript = $("#transcript");
const analyzeBtn = $("#analyze-btn");
const uploadSection = $("#upload-section");
const loading = $("#loading");
const loadingText = $("#loading-text");
const results = $("#results");
const resetBtn = $("#reset-btn");
const recipientInput = $("#recipient");
const toast = $("#toast");
const errorBanner = $("#error-banner");
const errorText = $("#error-text");

let files = [];

function isImageFile(file) {
  if (file.type && file.type.startsWith("image/")) return true;
  const ext = file.name.split(".").pop()?.toLowerCase();
  return ext ? IMAGE_EXTENSIONS.has(ext) : false;
}

function updateAnalyzeBtn() {
  const hasFiles = files.length > 0;
  const hasText = transcript.value.trim().length > 0;
  analyzeBtn.disabled = !(hasFiles || hasText);
}

function clearError() {
  errorBanner.classList.add("hidden");
  errorText.textContent = "";
}

function showError(message) {
  errorText.textContent = message;
  errorBanner.classList.remove("hidden");
}

function renderPreviews() {
  previews.innerHTML = "";
  if (files.length === 0) {
    previews.classList.add("hidden");
    return;
  }

  previews.classList.remove("hidden");
  files.forEach((file, i) => {
    const div = document.createElement("div");
    div.className = "preview";

    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    img.onload = () => URL.revokeObjectURL(img.src);

    const btn = document.createElement("button");
    btn.className = "preview__remove";
    btn.textContent = "×";
    btn.onclick = (e) => {
      e.stopPropagation();
      files.splice(i, 1);
      renderPreviews();
      updateAnalyzeBtn();
    };

    div.append(img, btn);
    previews.appendChild(div);
  });
}

function addFiles(newFiles) {
  clearError();
  let rejected = 0;
  for (const f of newFiles) {
    if (isImageFile(f)) {
      files.push(f);
    } else {
      rejected++;
    }
  }
  if (rejected > 0 && files.length === 0) {
    showError("Couldn't read that file. Try PNG or JPG screenshots.");
  }
  renderPreviews();
  updateAnalyzeBtn();
}

dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  addFiles([...fileInput.files]);
  fileInput.value = "";
});

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  addFiles([...e.dataTransfer.files]);
});

transcript.addEventListener("input", () => {
  clearError();
  updateAnalyzeBtn();
});

function setLoadingStep(step) {
  const steps = loading.querySelectorAll(".step");
  const order = ["read", "analyze", "generate"];
  const idx = order.indexOf(step);

  steps.forEach((el, i) => {
    el.classList.remove("active", "done");
    if (i < idx) el.classList.add("done");
    else if (i === idx) el.classList.add("active");
  });
}

function showToast(msg = "Copied") {
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2500);
}

function parseErrorDetail(detail) {
  if (!detail) return "Something went wrong. Try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || String(d)).join(". ");
  }
  return String(detail);
}

async function analyze() {
  clearError();

  const hasFiles = files.length > 0;
  const hasText = transcript.value.trim().length > 0;
  if (!hasFiles && !hasText) {
    showError("Add a screenshot or paste the conversation first.");
    return;
  }

  uploadSection.classList.add("hidden");
  loading.classList.remove("hidden");
  results.classList.add("hidden");
  analyzeBtn.disabled = true;

  const form = new FormData();
  const text = transcript.value.trim();

  if (text) {
    form.append("text", text);
    setLoadingStep("analyze");
    loadingText.textContent = "Analyzing conversation...";
  } else {
    files.forEach((f) => form.append("files", f));
    setLoadingStep("read");
    loadingText.textContent = "Reading screenshots...";

    setTimeout(() => {
      if (!loading.classList.contains("hidden")) {
        setLoadingStep("analyze");
        loadingText.textContent = "Breaking down the argument...";
      }
    }, 2500);

    setTimeout(() => {
      if (!loading.classList.contains("hidden")) {
        setLoadingStep("generate");
        loadingText.textContent = "Generating responses...";
      }
    }, 5500);
  }

  try {
    const res = await fetch("/api/analyze", { method: "POST", body: form });
    const raw = await res.text();
    let data;
    try {
      data = JSON.parse(raw);
    } catch {
      throw new Error(
        raw.trim().slice(0, 200) || "Server returned an invalid response. Is the app running?"
      );
    }

    if (!res.ok) {
      throw new Error(parseErrorDetail(data.detail));
    }

    renderResults(data);
    loading.classList.add("hidden");
    results.classList.remove("hidden");
  } catch (err) {
    loading.classList.add("hidden");
    uploadSection.classList.remove("hidden");
    showError(err.message || "Something went wrong. Try again.");
  } finally {
    updateAnalyzeBtn();
  }
}

function renderResults(data) {
  $("#situation").textContent = data.situation;
  $("#breakdown").textContent = data.breakdown;
  $("#approach").textContent = data.best_approach;
  $("#conversation").textContent = data.conversation;

  const container = $("#responses");
  container.innerHTML = "";

  for (let level = 1; level <= 5; level++) {
    const text = data.responses[String(level)];
    const isRec = level === data.recommended_level;

    const card = document.createElement("article");
    card.className = `response${isRec ? " recommended" : ""}`;
    card.style.animationDelay = `${level * 0.06}s`;

    const recipient = recipientInput.value.trim();
    const smsHref = recipient
      ? `sms:${encodeURIComponent(recipient)}&body=${encodeURIComponent(text)}`
      : null;

    card.innerHTML = `
      <div class="response__level response__level--${level}">${level}</div>
      <div class="response__body">
        <div class="response__label">
          ${LEVEL_LABELS[level]}
          ${isRec ? '<span class="response__badge">Recommended</span>' : ""}
        </div>
        <p class="response__text"></p>
      </div>
      <div class="response__actions">
        <button class="response__copy">Copy</button>
        ${smsHref ? `<a class="response__send" href="${smsHref}">Send in Messages</a>` : ""}
      </div>
    `;

    card.querySelector(".response__text").textContent = text;

    const copyBtn = card.querySelector(".response__copy");
    copyBtn.addEventListener("click", async () => {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied";
      copyBtn.classList.add("copied");
      showToast("Copied to clipboard");
      setTimeout(() => {
        copyBtn.textContent = "Copy";
        copyBtn.classList.remove("copied");
      }, 2000);
    });

    container.appendChild(card);
  }
}

function reset() {
  files = [];
  transcript.value = "";
  renderPreviews();
  clearError();
  updateAnalyzeBtn();
  results.classList.add("hidden");
  uploadSection.classList.remove("hidden");
  setLoadingStep("read");
}

analyzeBtn.addEventListener("click", analyze);
resetBtn.addEventListener("click", reset);

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (!data.ok) showError(data.error);
  } catch {
    showError("Can't reach the server. Run ./run.sh to start the app.");
  }
}

checkHealth();
updateAnalyzeBtn();
