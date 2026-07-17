/* ============================================================
   ChatPDF Agente — app.js
   Endpoints:
     GET  /api/v1/documents
     POST /api/v1/documents/upload
     POST /api/v1/documents/upload-many
     DELETE /api/v1/documents/:id
     GET  /api/v1/documents/:id/pages
     POST /api/v1/chat/ask
     POST /api/v1/chat/summary
     POST /api/v1/chat/questions
   ============================================================ */

// ── Estado global ─────────────────────────────────────────────
const state = {
  documents: [],
  selectedDocId: null,
  activeDocId: null,
  currentModel: 'llama3',
  lastSources: [],
  pdfText: {},
};

// ── DOM ───────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const llmSelect     = $('llm-select');
const llmBadge      = $('llm-badge');
const fileInput     = $('file-input');
const uploadLabel   = $('upload-label');
const uploadProg    = $('upload-progress');
const progressFill  = $('progress-fill');
const progressText  = $('progress-text');
const docsList      = $('docs-list');
const docsCount     = $('docs-count');
const filterLabel   = $('filter-label');
const btnFilterAll  = $('btn-filter-all');
const messagesEl    = $('messages');
const typingEl      = $('typing');
const questionInput = $('question-input');
const sendBtn       = $('send-btn');
const statusDot     = $('status-dot');
const chatDocFilter = $('chat-doc-filter');
const topbarStatus  = $('topbar-status');
const viewerDocName = $('viewer-doc-name');
const viewerPageNav = $('viewer-page-nav');
const btnPrev       = $('btn-prev-page');
const btnNext       = $('btn-next-page');
const curPageEl     = $('cur-page');
const totalPagesEl  = $('total-pages');
const btnClearHl    = $('btn-clear-highlight');
const viewerEmpty   = $('viewer-empty');
const pdfPages      = $('pdf-pages');

// ── LLM selector ──────────────────────────────────────────────
llmSelect.addEventListener('change', () => {
  state.currentModel = llmSelect.value;
  llmBadge.textContent = llmSelect.value;
});

// ── Subir archivos ────────────────────────────────────────────
fileInput.addEventListener('change', async () => {
  const files = Array.from(fileInput.files);
  if (!files.length) return;
  uploadLabel.textContent = files.length === 1 ? files[0].name : `${files.length} archivos`;
  showProgress(true, 'Subiendo...');
  animateProgress(30);
  try {
    let uploadedDocId = null;
    if (files.length === 1) {
      const fd = new FormData();
      fd.append('file', files[0]);
      const r = await fetch('/api/v1/documents/upload', { method: 'POST', body: fd });
      const d = await parseJson(r);
      if (!r.ok) throw new Error(d.detail || 'Error al subir');
      animateProgress(100);
      setTopbarStatus(`✓ ${d.file_name} — ${d.pages_processed} págs, ${d.chunks_created} chunks`, 'success');
      uploadedDocId = d.document_id;
    } else {
      const fd = new FormData();
      files.forEach(f => fd.append('files', f));
      const r = await fetch('/api/v1/documents/upload-many', { method: 'POST', body: fd });
      const d = await parseJson(r);
      if (!r.ok) throw new Error(d.detail || 'Error al subir');
      animateProgress(100);
      setTopbarStatus(`✓ ${d.processed_count} documentos procesados`, 'success');
      uploadedDocId = d.documents?.[0]?.document_id || null;
    }
    await loadDocuments();
    // Auto-seleccionar y cargar resumen del doc recién subido
    if (uploadedDocId) {
      const doc = state.documents.find(d => d.document_id === uploadedDocId);
      if (doc) {
        await openViewer(doc.document_id, doc.file_name, doc.total_pages);
        await loadDocumentContext(uploadedDocId);
      }
    }
  } catch (err) {
    setTopbarStatus(err.message, 'error');
  } finally {
    setTimeout(() => showProgress(false), 1200);
    fileInput.value = '';
    uploadLabel.textContent = 'Subir PDF';
  }
});

function showProgress(visible, text = '') {
  uploadProg.classList.toggle('visible', visible);
  if (visible) { progressFill.style.width = '5%'; progressText.textContent = text; }
}
function animateProgress(target) {
  let cur = parseFloat(progressFill.style.width) || 0;
  const step = () => {
    cur = Math.min(cur + (target - cur) * 0.15 + 1, target);
    progressFill.style.width = cur + '%';
    if (cur < target) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ── Cargar lista de documentos ────────────────────────────────
async function loadDocuments() {
  try {
    const r = await fetch('/api/v1/documents');
    const d = await parseJson(r);
    if (!r.ok) throw new Error(d.detail);
    state.documents = d.documents || [];
    renderDocuments();
  } catch (err) {
    docsList.innerHTML = `<div class="docs-empty" style="color:var(--danger)">${err.message}</div>`;
  }
}

function renderDocuments() {
  docsCount.textContent = state.documents.length;
  if (!state.documents.length) {
    docsList.innerHTML = '<div class="docs-empty">Sube un PDF para comenzar.</div>';
    return;
  }
  docsList.innerHTML = state.documents.map(doc => `
    <div class="doc-item ${state.activeDocId === doc.document_id ? 'active' : ''}" data-id="${doc.document_id}">
      <div class="doc-item-name" title="${esc(doc.file_name)}">${esc(doc.file_name)}</div>
      <div class="doc-item-meta">
        <span>${doc.total_pages} págs.</span>
        <span>${doc.chunks_count} chunks</span>
      </div>
      <div class="doc-item-actions">
        <button class="doc-action-btn ${state.selectedDocId === doc.document_id ? 'active' : ''}"
                data-action="filter" data-id="${doc.document_id}">
          ${state.selectedDocId === doc.document_id ? '✓ Filtrando' : 'Filtrar chat'}
        </button>
        <button class="doc-action-btn ${state.activeDocId === doc.document_id ? 'active' : ''}"
                data-action="view" data-id="${doc.document_id}"
                data-name="${esc(doc.file_name)}" data-pages="${doc.total_pages}">
          Ver PDF
        </button>
        <button class="doc-action-btn danger"
                data-action="delete" data-id="${doc.document_id}" data-name="${esc(doc.file_name)}">
          Eliminar
        </button>
      </div>
    </div>
  `).join('');

  docsList.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const id = Number(btn.dataset.id);
      if (btn.dataset.action === 'filter') toggleFilter(id);
      if (btn.dataset.action === 'view')   handleViewDoc(id, btn.dataset.name, Number(btn.dataset.pages));
      if (btn.dataset.action === 'delete') deleteDocument(id, btn.dataset.name);
    });
  });
}

// ── Ver doc: abre visor Y carga contexto (resumen + preguntas) ─
async function handleViewDoc(docId, docName, totalPages) {
  await openViewer(docId, docName, totalPages);
  await loadDocumentContext(docId);
}

// ── Resumen + Preguntas ───────────────────────────────────────
async function loadDocumentContext(docId) {
  const doc = state.documents.find(d => d.document_id === docId);
  if (!doc) return;

  // Mensaje de carga
  appendWelcomeLoading(doc.file_name);

  try {
    // Llamadas en paralelo
    const [sumRes, qRes] = await Promise.all([
      fetch('/api/v1/chat/summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: docId }),
      }),
      fetch('/api/v1/chat/questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: docId }),
      }),
    ]);

    const sumData = await parseJson(sumRes);
    const qData   = await parseJson(qRes);

    if (!sumRes.ok) throw new Error(sumData.detail || 'Error al generar resumen');
    if (!qRes.ok)   throw new Error(qData.detail   || 'Error al generar preguntas');

    replaceWelcomeLoading(sumData.summary, qData.questions || []);
  } catch (err) {
    replaceWelcomeLoading(`No se pudo generar el resumen: ${err.message}`, []);
  }
}

let welcomeMsgEl = null;

function appendWelcomeLoading(fileName) {
  // Eliminar mensaje anterior de bienvenida si existe
  if (welcomeMsgEl) { welcomeMsgEl.remove(); welcomeMsgEl = null; }

  welcomeMsgEl = document.createElement('div');
  welcomeMsgEl.className = 'msg bot welcome-msg';
  welcomeMsgEl.innerHTML = `
    <div class="msg-bubble">
      <div class="welcome-doc-name">📄 ${esc(shorten(fileName, 40))}</div>
      <div class="welcome-loading">
        <span class="loading-dot"></span>
        <span class="loading-dot"></span>
        <span class="loading-dot"></span>
        Generando resumen y preguntas sugeridas...
      </div>
    </div>
  `;
  messagesEl.appendChild(welcomeMsgEl);
  scrollChat();
}

function replaceWelcomeLoading(summary, questions) {
  if (!welcomeMsgEl) return;
  const fileName = welcomeMsgEl.querySelector('.welcome-doc-name')?.textContent || '';

  let questionsHtml = '';
  if (questions.length) {
    const chips = questions.map((q, i) => `
      <button class="question-chip" data-q="${esc(q)}">
        <span class="q-icon">?</span>
        <span class="q-text">${esc(q)}</span>
      </button>
    `).join('');
    questionsHtml = `
      <div class="suggested-questions">
        <div class="sq-label">Preguntas sugeridas — haz clic para preguntar</div>
        ${chips}
      </div>
    `;
  }

  welcomeMsgEl.innerHTML = `
    <div class="msg-bubble">
      <div class="welcome-doc-name">${fileName}</div>
      <div class="welcome-summary">${esc(summary)}</div>
      ${questionsHtml}
    </div>
  `;

  welcomeMsgEl.querySelectorAll('.question-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const q = chip.dataset.q;
      questionInput.value = q;
      sendQuestion();
    });
  });

  scrollChat();
}

// ── Filter / delete ───────────────────────────────────────────
function toggleFilter(id) {
  state.selectedDocId = state.selectedDocId === id ? null : id;
  const doc = state.documents.find(d => d.document_id === id);
  filterLabel.textContent = state.selectedDocId
    ? `Filtrando: ${doc ? shorten(doc.file_name, 22) : id}`
    : 'Sin filtro';
  chatDocFilter.textContent = state.selectedDocId
    ? `· ${doc ? shorten(doc.file_name, 20) : id}`
    : '';
  renderDocuments();
}

btnFilterAll.addEventListener('click', () => {
  state.selectedDocId = null;
  filterLabel.textContent = 'Sin filtro';
  chatDocFilter.textContent = '';
  renderDocuments();
});

async function deleteDocument(id, name) {
  if (!confirm(`¿Eliminar "${name}" del índice?`)) return;
  try {
    const r = await fetch(`/api/v1/documents/${id}`, { method: 'DELETE' });
    const d = await parseJson(r);
    if (!r.ok) throw new Error(d.detail);
    if (state.selectedDocId === id) toggleFilter(id);
    if (state.activeDocId === id) closeViewer();
    setTopbarStatus('Documento eliminado', 'success');
    await loadDocuments();
  } catch (err) {
    setTopbarStatus(err.message, 'error');
  }
}

// ── Visor PDF ─────────────────────────────────────────────────
let viewerPage = 1;
let viewerTotalPages = 1;

async function openViewer(docId, docName, totalPages) {
  state.activeDocId = docId;
  viewerPage = 1;
  viewerTotalPages = totalPages;
  viewerDocName.textContent = docName;
  viewerPageNav.style.display = 'flex';
  btnClearHl.style.display = 'inline-flex';
  viewerEmpty.style.display = 'none';
  pdfPages.style.display = 'flex';
  totalPagesEl.textContent = totalPages;
  curPageEl.textContent = 1;
  updateNavBtns();
  renderDocuments();

  if (!state.pdfText[docId]) {
    pdfPages.innerHTML = '<div class="pdf-page-loading">Cargando contenido...</div>';
    try {
      const r = await fetch(`/api/v1/documents/${docId}/pages`);
      if (r.ok) {
        const d = await r.json();
        state.pdfText[docId] = d.pages || [];
      } else {
        state.pdfText[docId] = buildPlaceholderPages(totalPages);
      }
    } catch {
      state.pdfText[docId] = buildPlaceholderPages(totalPages);
    }
  }
  renderViewerPages();
}

function buildPlaceholderPages(n) {
  return Array.from({ length: n }, (_, i) => ({
    page: i + 1,
    text: `Página ${i + 1}\n\nContenido en carga...`,
  }));
}

function renderViewerPages(highlightSnippets = []) {
  const pages = state.pdfText[state.activeDocId] || [];
  if (!pages.length) { pdfPages.innerHTML = ''; return; }
  pdfPages.innerHTML = pages.map(p => {
    let text = esc(p.text);
    highlightSnippets.forEach(snippet => {
      if (!snippet || snippet.length < 10) return;
      extractKeywords(snippet).forEach(kw => {
        if (kw.length < 4) return;
        const re = new RegExp(`(${escRe(esc(kw))})`, 'gi');
        text = text.replace(re, '<span class="pdf-hl">$1</span>');
      });
    });
    return `
      <div class="pdf-page ${highlightSnippets.length ? 'highlighted' : ''}" id="pdf-pg-${p.page}">
        <div style="white-space:pre-wrap;">${text}</div>
        <div class="pdf-page-num">${p.page}</div>
      </div>
    `;
  }).join('');
  scrollToPage(viewerPage);
}

function scrollToPage(n) {
  const el = document.getElementById(`pdf-pg-${n}`);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  viewerPage = n;
  curPageEl.textContent = n;
  updateNavBtns();
}

function updateNavBtns() {
  btnPrev.disabled = viewerPage <= 1;
  btnNext.disabled = viewerPage >= viewerTotalPages;
}

btnPrev.addEventListener('click', () => { if (viewerPage > 1) scrollToPage(viewerPage - 1); });
btnNext.addEventListener('click', () => { if (viewerPage < viewerTotalPages) scrollToPage(viewerPage + 1); });

btnClearHl.addEventListener('click', () => renderViewerPages([]));

function closeViewer() {
  state.activeDocId = null;
  viewerDocName.textContent = 'Ningún documento seleccionado';
  viewerPageNav.style.display = 'none';
  btnClearHl.style.display = 'none';
  viewerEmpty.style.display = 'flex';
  pdfPages.style.display = 'none';
  pdfPages.innerHTML = '';
  renderDocuments();
}

// ── Chat ──────────────────────────────────────────────────────
questionInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuestion(); }
});
sendBtn.addEventListener('click', sendQuestion);

async function sendQuestion() {
  const q = questionInput.value.trim();
  if (!q) return;
  questionInput.value = '';
  appendMessage('user', q);
  setStatusDot('loading');
  typingEl.classList.add('visible');
  sendBtn.disabled = true;

  try {
    const r = await fetch('/api/v1/chat/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: q,
        top_k: 3,
        document_id: state.selectedDocId || null,
        model: state.currentModel,
      }),
    });
    const d = await parseJson(r);
    if (!r.ok) throw new Error(d.detail || 'Error al consultar');
    state.lastSources = d.sources || [];
    appendBotMessage(d.answer, d.sources || [], q);
    setStatusDot('online');

    if (state.activeDocId && state.lastSources.length) {
      renderViewerPages(state.lastSources.map(s => s.snippet));
      const firstPage = state.lastSources[0]?.page_number;
      if (firstPage) scrollToPage(firstPage);
    }
    if (!state.activeDocId && state.lastSources.length) {
      const src = state.lastSources[0];
      const doc = state.documents.find(d =>
        d.file_name === src.file_name || d.document_id === state.selectedDocId
      );
      if (doc) await openViewer(doc.document_id, doc.file_name, doc.total_pages);
    }
  } catch (err) {
    appendMessage('bot', `⚠ ${err.message}`);
    setStatusDot('');
  } finally {
    typingEl.classList.remove('visible');
    sendBtn.disabled = false;
  }
}

function appendMessage(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.innerHTML = `<div class="msg-bubble">${esc(text)}</div>`;
  messagesEl.appendChild(div);
  scrollChat();
}

function appendBotMessage(answer, sources, question) {
  const div = document.createElement('div');
  div.className = 'msg bot';
  let highlighted = esc(answer);
  if (sources.length) {
    extractKeywords(question).forEach(kw => {
      if (kw.length < 4) return;
      const re = new RegExp(`(${escRe(esc(kw))})`, 'gi');
      highlighted = highlighted.replace(re, '<span class="inline-hl">$1</span>');
    });
  }
  let html = `<div class="msg-bubble">${highlighted}</div>`;
  if (sources.length) {
    html += `<div class="msg-sources">${sources.map((s, i) => `
      <span class="src-chip" data-src-idx="${i}" title="${esc(s.snippet)}">
        <span class="src-icon">📄</span>
        ${esc(shorten(s.file_name, 20))}
        <span class="src-page">· p.${s.page_number}</span>
      </span>
    `).join('')}</div>`;
  }
  div.innerHTML = html;
  div.querySelectorAll('.src-chip').forEach(chip => {
    chip.addEventListener('click', () => jumpToSource(sources[Number(chip.dataset.srcIdx)]));
  });
  div.querySelectorAll('.inline-hl').forEach(hl => {
    hl.addEventListener('click', () => { if (sources[0]) jumpToSource(sources[0]); });
  });
  messagesEl.appendChild(div);
  scrollChat();
}

function jumpToSource(src) {
  if (!state.activeDocId) {
    const doc = state.documents.find(d => d.file_name === src.file_name);
    if (doc) openViewer(doc.document_id, doc.file_name, doc.total_pages).then(() => scrollToPage(src.page_number));
    return;
  }
  scrollToPage(src.page_number);
  const pageEl = document.getElementById(`pdf-pg-${src.page_number}`);
  if (pageEl) {
    pageEl.classList.add('highlighted');
    pageEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setTimeout(() => pageEl.classList.remove('highlighted'), 3000);
  }
}

function scrollChat() { messagesEl.scrollTop = messagesEl.scrollHeight; }
function setStatusDot(s) { statusDot.className = 'status-dot' + (s ? ` ${s}` : ''); }

// ── Utilidades ────────────────────────────────────────────────
function esc(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}
function shorten(str, n) { return str.length > n ? str.slice(0, n) + '…' : str; }
function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
function extractKeywords(q) {
  return [...new Set((q.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').match(/[a-z0-9]{4,}/g) || []))];
}
async function parseJson(r) {
  const ct = r.headers.get('content-type') || '';
  if (ct.includes('application/json')) return r.json();
  return { detail: await r.text() };
}
function setTopbarStatus(msg, type = '') {
  topbarStatus.textContent = msg;
  topbarStatus.className = 'topbar-status' + (type ? ` ${type}` : '');
  if (type) setTimeout(() => { topbarStatus.textContent = ''; topbarStatus.className = 'topbar-status'; }, 4000);
}

// ── Init ──────────────────────────────────────────────────────
loadDocuments();
setStatusDot('online');
