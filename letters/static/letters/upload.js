(function () {
  const C = window.GENDALF;
  const $ = id => document.getElementById(id);
  const input = $('pdfInput'), editor = $('editor'), frame = $('pdfFrame');
  const saveBtn = $('saveBtn'), dlg = $('saveDlg'), status = $('status');
  let pdfUrl = null, baseName = '', dirHandle = null, pageMeta = null;

  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  const store = {
    get: k => { try { return localStorage.getItem(k) || ''; } catch (e) { return ''; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} },
  };

  // ---------- загрузка и преобразование ----------
  async function handleFile(file) {
    if (!file) return;
    if (!/\.pdf$/i.test(file.name)) { alert('Нужен файл в формате PDF.'); return; }
    if (file.size > C.maxMb * 1048576) { alert('Файл больше ' + C.maxMb + ' МБ.'); return; }
    $('fileName').textContent = file.name;
    baseName = file.name.replace(/\.pdf$/i, '');
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    pdfUrl = URL.createObjectURL(file);
    frame.src = pdfUrl; frame.style.display = 'block'; $('pdfPh').hidden = true;
    editor.style.display = 'none'; $('docPh').hidden = true; pageMeta = null; $('docPh').textContent = 'Здесь появится WORD-документ после обработки'; saveBtn.disabled = true;
    $('busy').hidden = false; status.textContent = '';
    const fd = new FormData(); fd.append('pdf', file);
    try {
      const r = await fetch(C.convertUrl, {method: 'POST', body: fd, headers: {'X-CSRFToken': csrf()}});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Ошибка обработки');
      editor.innerHTML = data.html || '<p></p>';
      pageMeta = data.page || null;
      layoutEditor();
      editor.style.display = 'block'; $('docPh').hidden = true;
      saveBtn.disabled = false;
      let msg = 'Страниц: ' + data.pages + (data.ocr_pages ? ' (распознано OCR: ' + data.ocr_pages + (data.ocrmypdf ? ', Tesseract + OCRmyPDF' : ', Tesseract') + ')' : '');
      if (data.warnings && data.warnings.length) msg += ' · ' + data.warnings.join(' ');
      status.textContent = msg;
    } catch (e) {
      $('docPh').hidden = false; $('docPh').textContent = 'Ошибка: ' + e.message;
    } finally { $('busy').hidden = true; }
  }
  // Редактор повторяет страницу оригинала: ширина и поля в pt, масштаб подгоняется под панель
  function layoutEditor() {
    if (!pageMeta) { editor.removeAttribute('style'); editor.style.display = 'block'; return; }
    const m = pageMeta;
    editor.style.display = 'block';
    editor.style.maxWidth = 'none';
    editor.style.width = m.w + 'pt';
    editor.style.padding = m.mt + 'pt ' + m.mr + 'pt ' + Math.max(m.mb, 28) + 'pt ' + m.ml + 'pt';
    const pane = editor.parentElement;
    const fit = (pane.clientWidth - 32) / (m.w * 96 / 72);
    editor.style.zoom = fit < 1 ? fit.toFixed(3) : '';
    editor.style.margin = '16px auto';
  }
  window.addEventListener('resize', () => { if (pageMeta && editor.style.display === 'block') layoutEditor(); });
  input.addEventListener('change', () => { handleFile(input.files[0]); input.value = ''; });
  ['dragenter', 'dragover'].forEach(ev => document.addEventListener(ev, e => { e.preventDefault(); document.body.classList.add('drag'); }));
  ['dragleave', 'drop'].forEach(ev => document.addEventListener(ev, e => { e.preventDefault(); document.body.classList.remove('drag'); }));
  document.addEventListener('drop', e => handleFile(e.dataTransfer.files[0]));

  // ---------- панель редактора ----------
  $('tools').addEventListener('mousedown', e => { if (e.target.closest('button')) e.preventDefault(); });
  $('tools').addEventListener('click', e => {
    const b = e.target.closest('button[data-cmd]'); if (!b) return;
    editor.focus(); document.execCommand(b.dataset.cmd, false, null);
  });
  $('blockSel').addEventListener('change', e => {
    editor.focus(); document.execCommand('formatBlock', false, e.target.value); e.target.value = 'p';
  });

  // ---------- диалог сохранения ----------
  const canDir = typeof window.showDirectoryPicker === 'function';
  const canFile = typeof window.showSaveFilePicker === 'function';
  $('dirHint').textContent = canDir
    ? 'Выберите папку на вашем компьютере — файл будет записан в неё. Поле можно править: оно попадёт в таблицу СКАНЫ как путь.'
    : 'Ваш браузер не даёт выбрать папку на странице по http — файл скачается в папку загрузок (или спросит место). ' +
      'Введите путь, куда вы его положите — он попадёт в таблицу СКАНЫ.';
  if (!canDir) $('pickDir').hidden = true;

  saveBtn.addEventListener('click', () => {
    $('fName').value = $('fName').value || baseName;
    $('fFolder').value = $('fFolder').value || store.get('gendalf.folder');
    $('dlgErr').hidden = true; dlg.showModal();
  });
  $('cancelSave').addEventListener('click', () => dlg.close());

  $('pickDir').addEventListener('click', async () => {
    try {
      dirHandle = await window.showDirectoryPicker({mode: 'readwrite'});
      if (!$('fFolder').value) $('fFolder').value = dirHandle.name;
      $('dirHint').textContent = 'Выбрана папка: «' + dirHandle.name + '». Полный путь браузер не сообщает — впишите его в поле выше.';
    } catch (e) { /* отмена */ }
  });

  function showErr(m) { $('dlgErr').textContent = m; $('dlgErr').hidden = false; }

  $('saveForm').addEventListener('submit', async e => {
    e.preventDefault();
    const name = $('fName').value.trim().replace(/[\\/:*?"<>|]/g, '_').replace(/\.docx$/i, '');
    if (!name) return showErr('Укажите название файла.');
    const folder = $('fFolder').value.trim();
    const btn = $('confirmSave'); btn.disabled = true;
    try {
      // 1) место сохранения выбираем сразу, пока действует клик пользователя
      let writer = null;
      if (dirHandle) {
        const fh = await dirHandle.getFileHandle(name + '.docx', {create: true});
        writer = await fh.createWritable();
      } else if (canFile) {
        const fh = await window.showSaveFilePicker({
          suggestedName: name + '.docx',
          types: [{description: 'Документ Word', accept: {'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']}}]});
        writer = await fh.createWritable();
      }
      // 2) сервер собирает WORD из текущего содержимого редактора
      const fd = new FormData();
      fd.append('html', editor.innerHTML); fd.append('filename', name);
      if (pageMeta) fd.append('page', JSON.stringify(pageMeta));
      const r = await fetch(C.docxUrl, {method: 'POST', body: fd, headers: {'X-CSRFToken': csrf()}});
      if (!r.ok) throw new Error('Не удалось собрать WORD-файл.');
      const blob = await r.blob();
      // 3) запись на машину пользователя
      if (writer) { await writer.write(blob); await writer.close(); }
      else {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = name + '.docx';
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 10000);
      }
      // 4) запись в таблицу СКАНЫ
      const rr = await fetch(C.registerUrl, {method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf()},
        body: JSON.stringify({filename: name, folder: folder, incoming_number: $('fNum').value, processed_date: $('fDate').value})});
      if (!rr.ok) throw new Error('Файл сохранён, но запись в таблицу СКАНЫ не создана.');
      store.set('gendalf.folder', folder);
      dlg.close();
      status.textContent = '✓ Сохранено: ' + name + '.docx';
    } catch (err) {
      if (err && err.name === 'AbortError') { /* пользователь отменил выбор */ }
      else showErr(err.message || String(err));
    } finally { btn.disabled = false; }
  });
})();
