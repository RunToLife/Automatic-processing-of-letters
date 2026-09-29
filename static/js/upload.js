(function () {
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

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
      const resp = await fetch("/api/recognize", {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
        body: formData,
      });
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
    saveModal.classList.add("open");
  });

  cancelSaveBtn.addEventListener("click", () => {
    saveModal.classList.remove("open");
  });

  // Сохраняет Blob на компьютер пользователя: если браузер поддерживает
  // File System Access API (Chrome/Edge) - открывается системный диалог
  // "Сохранить как" с выбором папки; иначе - обычная загрузка файла
  // через ссылку (попадает в папку загрузок браузера).
  async function saveBlobToUserComputer(blob, suggestedName) {
    if (window.showSaveFilePicker) {
      try {
        const handle = await window.showSaveFilePicker({
          suggestedName: suggestedName,
          types: [{
            description: "WORD документ",
            accept: { "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"] },
          }],
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        return;
      } catch (e) {
        if (e && e.name === "AbortError") {
          throw e; // пользователь отменил диалог сохранения
        }
        // API недоступен по иной причине - используем запасной вариант ниже
      }
    }

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = suggestedName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

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
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify({
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

      const fileResp = await fetch(data.download_url);
      if (!fileResp.ok) {
        alert("Файл сохранён на сервере, но не удалось получить его для загрузки на компьютер.");
        return;
      }
      const blob = await fileResp.blob();

      try {
        await saveBlobToUserComputer(blob, data.filename);
      } catch (e) {
        if (e && e.name === "AbortError") {
          statusLabel.textContent = "Сохранение отменено пользователем.";
          return;
        }
        throw e;
      }

      saveModal.classList.remove("open");
      statusLabel.textContent = "Файл сохранён на ваш компьютер: " + data.filename;
    } catch (e) {
      alert("Не удалось сохранить файл: " + e);
    } finally {
      confirmSaveBtn.disabled = false;
    }
  });
})();
