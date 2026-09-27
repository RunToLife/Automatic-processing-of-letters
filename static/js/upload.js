(function () {
  const pdfInput = document.getElementById("pdfInput");
  const recognizeBtn = document.getElementById("recognizeBtn");
  const statusLabel = document.getElementById("statusLabel");
  const splitView = document.getElementById("splitView");
  const pdfFrame = document.getElementById("pdfFrame");
  const docxText = document.getElementById("docxText");
  const saveWordBtn = document.getElementById("saveWordBtn");

  const saveModal = document.getElementById("saveModal");
  const fileNameInput = document.getElementById("fileNameInput");
  const incomingNumberInput = document.getElementById("incomingNumberInput");
  const processedDateInput = document.getElementById("processedDateInput");
  const cancelSaveBtn = document.getElementById("cancelSaveBtn");
  const confirmSaveBtn = document.getElementById("confirmSaveBtn");

  const browserPath = document.getElementById("browserPath");
  const browserList = document.getElementById("browserList");
  const newFolderName = document.getElementById("newFolderName");
  const createFolderBtn = document.getElementById("createFolderBtn");

  let currentFolder = "";

  pdfInput.addEventListener("change", () => {
    recognizeBtn.disabled = !pdfInput.files.length;
  });

  recognizeBtn.addEventListener("click", async () => {
    if (!pdfInput.files.length) return;
    const file = pdfInput.files[0];
    const formData = new FormData();
    formData.append("pdf_file", file);

    recognizeBtn.disabled = true;
    statusLabel.textContent = "Распознавание письма, это может занять некоторое время...";

    try {
      const resp = await fetch("/api/recognize", { method: "POST", body: formData });
      const data = await resp.json();
      if (!resp.ok) {
        statusLabel.textContent = "";
        alert(data.error || "Ошибка распознавания");
        recognizeBtn.disabled = false;
        return;
      }
      pdfFrame.src = data.pdf_url;
      docxText.value = data.text;
      fileNameInput.value = data.suggested_filename || "";
      splitView.style.display = "flex";
      statusLabel.textContent = "Готово. Проверьте и при необходимости отредактируйте текст.";
    } catch (e) {
      statusLabel.textContent = "";
      alert("Не удалось выполнить запрос: " + e);
    } finally {
      recognizeBtn.disabled = false;
    }
  });

  saveWordBtn.addEventListener("click", () => {
    incomingNumberInput.value = "";
    const today = new Date().toISOString().slice(0, 10);
    processedDateInput.value = today;
    currentFolder = "";
    loadBrowser("");
    saveModal.classList.add("open");
  });

  cancelSaveBtn.addEventListener("click", () => {
    saveModal.classList.remove("open");
  });

  async function loadBrowser(path) {
    const resp = await fetch("/api/browse?path=" + encodeURIComponent(path));
    const data = await resp.json();
    if (!resp.ok) {
      alert(data.error || "Ошибка загрузки папок");
      return;
    }
    currentFolder = data.current;
    browserPath.textContent = data.root_label + (data.current ? "/" + data.current : "");
    browserList.innerHTML = "";

    if (data.parent !== null) {
      const up = document.createElement("div");
      up.className = "up-item";
      up.textContent = "⬆ Вверх";
      up.addEventListener("click", () => loadBrowser(data.parent));
      browserList.appendChild(up);
    }

    data.dirs.forEach((name) => {
      const item = document.createElement("div");
      item.className = "dir-item";
      item.textContent = "📁 " + name;
      item.addEventListener("dblclick", () => {
        const next = data.current ? data.current + "/" + name : name;
        loadBrowser(next);
      });
      browserList.appendChild(item);
    });
  }

  createFolderBtn.addEventListener("click", async () => {
    const name = newFolderName.value.trim();
    if (!name) return;
    const resp = await fetch("/api/browse/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: currentFolder, name: name }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      alert(data.error || "Не удалось создать папку");
      return;
    }
    newFolderName.value = "";
    loadBrowser(currentFolder);
  });

  confirmSaveBtn.addEventListener("click", async () => {
    const filename = fileNameInput.value.trim();
    const incomingNumber = incomingNumberInput.value.trim();
    const processedDate = processedDateInput.value;

    if (!filename) { alert("Укажите название файла"); return; }
    if (!incomingNumber) { alert("Укажите № входящего письма"); return; }

    confirmSaveBtn.disabled = true;
    try {
      const resp = await fetch("/api/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          folder: currentFolder,
          filename: filename,
          incoming_number: incomingNumber,
          processed_date: processedDate,
          text: docxText.value,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        alert(data.error || "Ошибка сохранения");
        return;
      }
      saveModal.classList.remove("open");
      statusLabel.textContent = "Файл сохранён: " + data.path;
    } catch (e) {
      alert("Не удалось сохранить файл: " + e);
    } finally {
      confirmSaveBtn.disabled = false;
    }
  });
})();
