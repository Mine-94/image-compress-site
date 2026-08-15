(function () {
  const I18N = window.I18N || {
    invalid_file: "JPG, PNG, WEBP 파일만 업로드할 수 있습니다.",
    generic_error: "처리 중 오류가 발생했습니다.",
    network_error: "네트워크 오류가 발생했습니다. 다시 시도해주세요.",
    already_optimized: "이미 최적화됨",
    ratio_suffix: "% 감소",
    dimension_note: "크기: {orig} → {new}",
    dimension_no_change: "크기: {orig} (변경 없음)",
  };

  const dropZone = document.getElementById("drop-zone");
  if (!dropZone) return;

  const fileInput = document.getElementById("file-input");
  const browseBtn = document.getElementById("browse-btn");

  const emptyView = document.getElementById("drop-zone-empty");
  const selectedView = document.getElementById("file-selected");
  const loadingView = document.getElementById("loading");
  const resultView = document.getElementById("result");
  const errorView = document.getElementById("error");

  const fileNameEl = document.getElementById("file-name");
  const fileSizeEl = document.getElementById("file-size");
  const compressBtn = document.getElementById("compress-btn");
  const errorTextEl = document.getElementById("error-text");

  const originalSizeEl = document.getElementById("original-size");
  const compressedSizeEl = document.getElementById("compressed-size");
  const ratioBadgeEl = document.getElementById("ratio-badge");
  const dimensionNoteEl = document.getElementById("dimension-note");
  const downloadLink = document.getElementById("download-link");

  let currentFile = null;
  const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

  function humanSize(bytes) {
    if (bytes < 1024) return bytes + "B";
    const units = ["KB", "MB", "GB"];
    let size = bytes / 1024;
    let i = 0;
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024;
      i++;
    }
    return size.toFixed(1) + units[i];
  }

  function showView(view) {
    [emptyView, selectedView, loadingView, resultView, errorView].forEach((v) =>
      v.classList.add("hidden")
    );
    view.classList.remove("hidden");
  }

  function reset() {
    currentFile = null;
    fileInput.value = "";
    showView(emptyView);
  }

  function onFileChosen(file) {
    if (!file) return;
    if (!ALLOWED_TYPES.includes(file.type)) {
      errorTextEl.textContent = I18N.invalid_file;
      showView(errorView);
      return;
    }
    currentFile = file;
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = humanSize(file.size);
    showView(selectedView);
  }

  browseBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => onFileChosen(e.target.files[0]));

  ["dragenter", "dragover"].forEach((evt) =>
    dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
    })
  );
  dropZone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    onFileChosen(file);
  });

  document.getElementById("reset-btn").addEventListener("click", reset);
  document.getElementById("reset-btn-2").addEventListener("click", reset);
  document.getElementById("reset-btn-3").addEventListener("click", reset);

  compressBtn.addEventListener("click", async () => {
    if (!currentFile) return;
    const quality = document.querySelector('input[name="quality"]:checked').value;
    const resize = document.querySelector('input[name="resize"]:checked').value;

    showView(loadingView);

    const formData = new FormData();
    formData.append("file", currentFile);
    formData.append("quality", quality);
    formData.append("resize", resize);
    formData.append("lang", window.APP_LANG || "ko");

    try {
      const res = await fetch("/api/process", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (!res.ok) {
        errorTextEl.textContent = data.error || I18N.generic_error;
        showView(errorView);
        return;
      }

      originalSizeEl.textContent = data.original_size_human;
      compressedSizeEl.textContent = data.compressed_size_human;
      ratioBadgeEl.textContent = data.used_original
        ? I18N.already_optimized
        : `${data.ratio}${I18N.ratio_suffix}`;
      dimensionNoteEl.textContent =
        data.original_dimensions === data.new_dimensions
          ? I18N.dimension_no_change.replace("{orig}", data.original_dimensions)
          : I18N.dimension_note
              .replace("{orig}", data.original_dimensions)
              .replace("{new}", data.new_dimensions);
      downloadLink.href = data.download_url;
      showView(resultView);
    } catch (err) {
      errorTextEl.textContent = I18N.network_error;
      showView(errorView);
    }
  });
})();
