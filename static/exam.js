/**
 * static/exam.js — Debug Dojo Formal Examination Controller
 * ==========================================================
 * Manages:
 *   • Attempt initiation and synchronization with authoritative server deadline.
 *   • Fullscreen toggle with graceful fallback.
 *   • Continuous countdown timer with 5m and 1m warnings (visual + text).
 *   • Anti-paste and anti-drag controls in the exam editor.
 *   • Logging of integrity events (paste attempts, blur, visibility change).
 *   • Running visible test cases and final exam submission.
 */

(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────────────────────────
  let currentAttempt = null;
  let timerInterval = null;
  let deadlineMs = 0;
  let isFinalized = false;
  let wasFullscreen = false;
  let integrityCount = 0;

  // ── DOM Elements ───────────────────────────────────────────────────────────
  const timerDisplay = document.getElementById('exam-timer-display');
  const timerContainer = document.getElementById('exam-timer-container');
  const timerWarningLabel = document.getElementById('exam-timer-warning');
  const statusBadge = document.getElementById('exam-status-badge');
  const learnerBadge = document.getElementById('exam-learner-badge');
  const challengeTitleEl = document.getElementById('exam-challenge-title');
  const difficultyBadge = document.getElementById('exam-difficulty-badge');
  const fullscreenBtn = document.getElementById('exam-fullscreen-btn');
  const fullscreenText = document.getElementById('fullscreen-text');
  const headerSubmitBtn = document.getElementById('exam-header-submit-btn');

  const questionTitle = document.getElementById('question-title');
  const questionNumberBadge = document.getElementById('question-number-badge');
  const questionTags = document.getElementById('question-concept-tags');
  const questionDesc = document.getElementById('question-description');
  const functionSignature = document.getElementById('function-signature');
  const visibleTestsPreview = document.getElementById('visible-tests-preview');

  const editor = document.getElementById('exam-editor');
  const resetBtn = document.getElementById('reset-code-btn');
  const runTestsBtn = document.getElementById('run-tests-btn');
  const submitExamBtn = document.getElementById('submit-exam-btn');
  const codeStatus = document.getElementById('code-status-indicator');

  const consoleOutput = document.getElementById('console-output');
  const consoleBadge = document.getElementById('console-badge');
  const collapseConsoleBtn = document.getElementById('collapse-console-btn');
  const resultsConsole = document.getElementById('results-console');

  const integrityBanner = document.getElementById('integrity-alert-banner');
  const integrityText = document.getElementById('integrity-alert-text');
  const integrityDismiss = document.getElementById('integrity-alert-dismiss');
  const toastContainer = document.getElementById('toast-container');

  const submitModal = document.getElementById('submit-modal');
  const modalCancelBtn = document.getElementById('modal-cancel-btn');
  const modalConfirmBtn = document.getElementById('modal-confirm-btn');
  const modalCloseBtn = document.getElementById('modal-close-btn');

  // ── Assistance Panel Tabs & Hints DOM Elements ────────────────────────────
  const tabQuestion = document.getElementById('exam-tab-question');
  const tabEditor = document.getElementById('exam-tab-editor');
  const tabHints = document.getElementById('exam-tab-hints');
  const tabAssistant = document.getElementById('exam-tab-assistant');
  const tabInstructions = document.getElementById('exam-tab-instructions');
  const panelQuestion = document.getElementById('exam-panel-question');
  const panelHints = document.getElementById('exam-panel-hints');
  const panelAssistant = document.getElementById('exam-panel-assistant');
  const panelInstructions = document.getElementById('exam-panel-instructions');
  const hintsTabBadge = document.getElementById('hints-tab-badge');

  const hintsProgressPill = document.getElementById('hints-progress-pill');
  const hintsList = document.getElementById('exam-hints-list');
  const hintsEmpty = document.getElementById('exam-hints-empty');
  const hintsLoading = document.getElementById('exam-hints-loading');
  const hintsError = document.getElementById('exam-hints-error');
  const requestHintBtn = document.getElementById('exam-request-hint-btn');
  const hintsBtnText = document.getElementById('hints-btn-text');
  const hintsExhausted = document.getElementById('exam-hints-exhausted');

  // ── AI Exam Assistant DOM Elements ────────────────────────────────────────
  const assistantMessages = document.getElementById('exam-assistant-messages');
  const assistantLoading = document.getElementById('exam-assistant-loading');
  const assistantError = document.getElementById('exam-assistant-error');
  const assistantForm = document.getElementById('exam-assistant-form');
  const assistantInput = document.getElementById('exam-assistant-input');
  const assistantSendBtn = document.getElementById('exam-assistant-send-btn');
  const assistantCharCount = document.getElementById('assistant-char-count');
  const assistantSuggestedPills = document.getElementById('assistant-suggested-pills');
  let lastVisibleTestSummary = '';

  // ── Initialization ─────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', init);

  async function init() {
    setupEventListeners();
    setupAntiPasteControls();
    setupExamAssistant();

    const params = new URLSearchParams(window.location.search);
    const attemptId = params.get('attempt_id');
    const challengeId = params.get('challenge_id') || localStorage.getItem('debug_dojo_last_exam_challenge');
    const learnerId = params.get('learner_id') || localStorage.getItem('debug_dojo_learner_id') || 'student1';
    const devDuration = params.get('duration'); // dev testing override

    if (attemptId) {
      await loadExistingAttempt(attemptId, challengeId, learnerId, devDuration);
    } else if (challengeId) {
      await startNewAttempt(challengeId, learnerId, devDuration);
    } else {
      renderErrorScreen('No challenge or examination attempt specified in URL.');
    }
  }

  // ── Attempt API Operations ─────────────────────────────────────────────────

  async function startNewAttempt(challengeId, learnerId, devDuration) {
    try {
      codeStatus.textContent = 'Connecting…';
      const payload = {
        challenge_id: challengeId,
        learner_id: learnerId,
      };
      if (devDuration && !isNaN(parseInt(devDuration, 10))) {
        payload.dev_duration = parseInt(devDuration, 10);
      }

      const res = await fetch('/api/exam/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        renderErrorScreen(err.detail || `Failed to start examination (${res.status}).`, challengeId);
        return;
      }

      const data = await res.json();
      currentAttempt = data;
      if (challengeId) {
        localStorage.setItem('debug_dojo_last_exam_challenge', challengeId);
      }

      // Update URL to include attempt_id and challenge_id without reloading
      const newUrl = `${window.location.pathname}?attempt_id=${encodeURIComponent(data.attempt_id)}&challenge_id=${encodeURIComponent(challengeId)}`;
      window.history.replaceState({ attemptId: data.attempt_id, challengeId: challengeId }, '', newUrl);

      renderExamUI(data);
      startAuthoritativeTimer(data.deadline, data.remaining_seconds);
    } catch (err) {
      renderErrorScreen(`Network failure connecting to examination backend: ${err.message}`, challengeId);
    }
  }

  async function loadExistingAttempt(attemptId, fallbackChallengeId, learnerId, devDuration) {
    try {
      codeStatus.textContent = 'Loading attempt…';
      const res = await fetch(`/api/exam/${encodeURIComponent(attemptId)}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        // If the attempt was lost (e.g. server restarted or redeployed), gracefully start a fresh attempt
        if (res.status === 404 && fallbackChallengeId) {
          console.warn(`Attempt ${attemptId} not found (server restart). Auto-starting fresh attempt for ${fallbackChallengeId}...`);
          await startNewAttempt(fallbackChallengeId, learnerId, devDuration);
          return;
        }
        renderErrorScreen(err.detail || `Examination attempt not found (${res.status}).`, fallbackChallengeId);
        return;
      }

      const data = await res.json();
      currentAttempt = data;
      if (data.challenge_id) {
        localStorage.setItem('debug_dojo_last_exam_challenge', data.challenge_id);
      }
      renderExamUI(data);

      if (data.status === 'submitted' || data.status === 'expired') {
        finalizeUIState(data.status, data.final_results);
      } else {
        startAuthoritativeTimer(data.deadline, data.remaining_seconds);
      }
    } catch (err) {
      renderErrorScreen(`Error loading examination attempt: ${err.message}`, fallbackChallengeId);
    }
  }

  // ── Render Examination Details ─────────────────────────────────────────────

  function renderExamUI(attempt) {
    const ch = attempt.challenge;
    learnerBadge.textContent = `Learner: ${attempt.learner_id}`;
    challengeTitleEl.textContent = ch.title;
    questionTitle.textContent = ch.title;
    questionNumberBadge.textContent = `Question: ${ch.id}`;

    // Difficulty badge
    const diff = ch.difficulty || 'easy';
    difficultyBadge.textContent = diff.toUpperCase();
    difficultyBadge.className = `badge badge--difficulty difficulty ${diff}`;

    // Status badge
    updateStatusBadge(attempt.status);

    // Tags
    questionTags.innerHTML = '';
    (ch.tags || []).forEach(t => {
      const sp = document.createElement('span');
      sp.className = 'concept-tag';
      sp.textContent = t;
      questionTags.appendChild(sp);
    });

    // Description
    questionDesc.innerHTML = formatMarkdown(ch.description || '');

    // Signature
    const firstLine = (ch.starter_code || '').split('\n').find(l => l.startsWith('def '));
    functionSignature.textContent = firstLine ? firstLine.replace(':', '') : `def ${ch.id}(...):`;

    // Visible tests preview
    visibleTestsPreview.innerHTML = '';
    (ch.visible_tests || []).forEach((vt, idx) => {
      const card = document.createElement('div');
      card.className = 'sample-test-card';
      card.innerHTML = `
        <div class="sample-test-label">${escapeHtml(vt.label || `Test Case #${idx + 1}`)}</div>
        <div class="sample-test-call"><code>${escapeHtml(vt.call)}</code></div>
        <div class="sample-test-exp">Expected return: <strong>${escapeHtml(vt.expected)}</strong></div>
      `;
      visibleTestsPreview.appendChild(card);
    });

    // Starter code
    if (attempt.submitted_code) {
      editor.value = attempt.submitted_code;
    } else {
      editor.value = ch.starter_code || '';
    }
    codeStatus.textContent = 'Ready';

    // Render progressive hints (restores any unlocked hints on load/refresh)
    renderHintsUI(attempt.unlocked_hints || []);
  }

  // ── Authoritative Timer ────────────────────────────────────────────────────

  function startAuthoritativeTimer(deadlineIso, remainingSeconds) {
    clearInterval(timerInterval);

    // Parse server deadline timestamp
    deadlineMs = new Date(deadlineIso).getTime();

    // Check if deadline already passed
    const now = Date.now();
    if (deadlineMs <= now || remainingSeconds <= 0) {
      handleTimeExpired();
      return;
    }

    updateTimerDisplay(Math.max(0, Math.floor((deadlineMs - now) / 1000)));

    timerInterval = setInterval(() => {
      const currentNow = Date.now();
      const remainingSec = Math.max(0, Math.floor((deadlineMs - currentNow) / 1000));
      updateTimerDisplay(remainingSec);

      if (remainingSec <= 0) {
        clearInterval(timerInterval);
        handleTimeExpired();
      }
    }, 1000);
  }

  function updateTimerDisplay(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    let text = '';
    if (hours > 0) {
      text = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    } else {
      text = `${pad(minutes)}:${pad(seconds)}`;
    }
    timerDisplay.textContent = text;

    // Warning indicators
    timerContainer.classList.remove('timer-warning-5m', 'timer-warning-1m', 'timer-expired');
    timerWarningLabel.textContent = '';

    if (totalSeconds <= 0) {
      timerContainer.classList.add('timer-expired');
      timerWarningLabel.textContent = 'EXPIRED';
    } else if (totalSeconds <= 60) {
      // 1 minute urgent warning
      timerContainer.classList.add('timer-warning-1m');
      timerWarningLabel.textContent = '🚨 <1m Left';
    } else if (totalSeconds <= 300) {
      // 5 minutes warning
      timerContainer.classList.add('timer-warning-5m');
      timerWarningLabel.textContent = '⚠ 5m Left';
    }
  }

  function pad(n) {
    return n < 10 ? '0' + n : '' + n;
  }

  async function handleTimeExpired() {
    if (isFinalized) return;
    isFinalized = true;

    updateTimerDisplay(0);
    updateStatusBadge('expired');
    editor.disabled = true;
    runTestsBtn.disabled = true;
    submitExamBtn.disabled = true;
    headerSubmitBtn.disabled = true;
    if (requestHintBtn) requestHintBtn.disabled = true;
    disableAssistantUI();

    showToast('Examination time has expired. The session is now closed.', 'urgent');
    logIntegrityEvent('time_expired', 'Authoritative deadline elapsed');

    // Attempt server finalization and retrieve results
    let serverResults = null;
    if (currentAttempt) {
      try {
        const res = await fetch(`/api/exam/${encodeURIComponent(currentAttempt.attempt_id)}/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: editor.value }),
        });
        if (res.ok) {
          serverResults = await res.json();
        }
      } catch (e) {
        // Server finalization failed — show results screen anyway
      }
    }

    // Show the results overlay with expired status
    showResultsScreen('expired', serverResults);
  }

  // ── Anti-Paste & Integrity Controls ────────────────────────────────────────

  function setupAntiPasteControls() {
    // 1. Intercept paste event
    editor.addEventListener('paste', e => {
      e.preventDefault();
      onPasteBlocked('Clipboard paste is disabled during examinations. Solutions must be typed.');
    });

    // 2. Intercept beforeinput (paste / clipboard insert)
    editor.addEventListener('beforeinput', e => {
      if (e.inputType && e.inputType.toLowerCase().includes('paste')) {
        e.preventDefault();
        onPasteBlocked('Pasting content is blocked in the examination environment.');
      }
    });

    // 3. Intercept key combinations: Ctrl+V, Cmd+V, Shift+Insert
    editor.addEventListener('keydown', e => {
      const isPasteCombo =
        ((e.ctrlKey || e.metaKey) && (e.key === 'v' || e.key === 'V')) ||
        (e.shiftKey && e.key === 'Insert');

      if (isPasteCombo) {
        e.preventDefault();
        onPasteBlocked('Keyboard shortcut for paste is disabled.');
        return;
      }

      // Tab key indentation support (insert 4 spaces)
      if (e.key === 'Tab') {
        e.preventDefault();
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        editor.value = editor.value.substring(0, start) + '    ' + editor.value.substring(end);
        editor.selectionStart = editor.selectionEnd = start + 4;
      }
    });

    // 4. Intercept drag and drop
    editor.addEventListener('dragover', e => e.preventDefault());
    editor.addEventListener('drop', e => {
      e.preventDefault();
      onPasteBlocked('Drag-and-drop code insertion is disabled.');
    });

    // 5. Intercept context menu on editor
    editor.addEventListener('contextmenu', e => {
      e.preventDefault();
      onPasteBlocked('Context menu is disabled on the code editor to prevent clipboard actions.');
    });

    // 6. Track tab visibility / window switch
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && !isFinalized) {
        logIntegrityEvent('tab_switch_hidden', 'Learner switched browser tab or minimized window');
      }
    });

    // 7. Track window blur
    window.addEventListener('blur', () => {
      if (!isFinalized) {
        logIntegrityEvent('window_blur', 'Examination window lost focus');
      }
    });

    // 8. Track fullscreen exit
    document.addEventListener('fullscreenchange', () => {
      const isNowFullscreen = !!document.fullscreenElement;
      if (wasFullscreen && !isNowFullscreen && !isFinalized) {
        logIntegrityEvent('fullscreen_exit', 'Learner exited fullscreen mode');
      }
      wasFullscreen = isNowFullscreen;
      updateFullscreenButtonUI(isNowFullscreen);
    });
  }

  function onPasteBlocked(message) {
    showToast(message, 'warning');
    logIntegrityEvent('paste_attempt', message);
  }

  async function logIntegrityEvent(eventType, details) {
    if (!currentAttempt || isFinalized) return;
    integrityCount++;

    if (integrityCount >= 3) {
      integrityBanner.classList.remove('hidden');
      integrityText.textContent = `Integrity Signal Alert (${integrityCount} events recorded). Tab switches, focus loss, and paste attempts are strictly audited.`;
    }

    try {
      await fetch(`/api/exam/${encodeURIComponent(currentAttempt.attempt_id)}/integrity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: eventType,
          details: details || '',
        }),
      });
    } catch (err) {
      // Background metric send failure ignored
    }
  }

  // ── Toast Notifications ───────────────────────────────────────────────────

  function showToast(text, type = 'warning') {
    const toast = document.createElement('div');
    toast.className = `exam-toast toast--${type}`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `<span class="toast-icon">⚠️</span> <span>${escapeHtml(text)}</span>`;

    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // ── Fullscreen Support ─────────────────────────────────────────────────────

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => {
        wasFullscreen = true;
        updateFullscreenButtonUI(true);
      }).catch(err => {
        showToast('Fullscreen mode could not be activated: ' + err.message, 'neutral');
      });
    } else {
      document.exitFullscreen().then(() => {
        wasFullscreen = false;
        updateFullscreenButtonUI(false);
      }).catch(err => {
        // Ignored
      });
    }
  }

  function updateFullscreenButtonUI(isFullscreen) {
    if (isFullscreen) {
      fullscreenText.textContent = 'Exit Fullscreen';
      fullscreenBtn.querySelector('.btn-icon').textContent = '🗗';
    } else {
      fullscreenText.textContent = 'Fullscreen';
      fullscreenBtn.querySelector('.btn-icon').textContent = '⛶';
    }
  }

  // ── Event Listeners Setup ──────────────────────────────────────────────────

  function setupEventListeners() {
    fullscreenBtn.addEventListener('click', toggleFullscreen);

    resetBtn.addEventListener('click', () => {
      if (isFinalized) return;
      if (currentAttempt && currentAttempt.challenge && currentAttempt.challenge.starter_code) {
        if (confirm('Reset your code to the original starter code?')) {
          editor.value = currentAttempt.challenge.starter_code;
        }
      }
    });

    runTestsBtn.addEventListener('click', runVisibleTests);

    headerSubmitBtn.addEventListener('click', () => {
      if (!isFinalized) submitModal.classList.remove('hidden');
    });

    submitExamBtn.addEventListener('click', () => {
      if (!isFinalized) submitModal.classList.remove('hidden');
    });

    modalCancelBtn.addEventListener('click', () => submitModal.classList.add('hidden'));
    modalCloseBtn.addEventListener('click', () => submitModal.classList.add('hidden'));
    modalConfirmBtn.addEventListener('click', () => {
      submitModal.classList.add('hidden');
      finalizeExamSubmission();
    });

    collapseConsoleBtn.addEventListener('click', () => {
      resultsConsole.classList.toggle('collapsed');
    });

    integrityDismiss.addEventListener('click', () => {
      integrityBanner.classList.add('hidden');
    });

    // Assistance Panel Tabs Event Listeners
    if (tabQuestion) tabQuestion.addEventListener('click', () => switchTab('question'));
    if (tabEditor) tabEditor.addEventListener('click', () => switchTab('editor'));
    if (tabHints) tabHints.addEventListener('click', () => switchTab('hints'));
    if (tabAssistant) tabAssistant.addEventListener('click', () => switchTab('assistant'));
    if (tabInstructions) tabInstructions.addEventListener('click', () => switchTab('instructions'));

    // Progressive Hint Request Button
    if (requestHintBtn) requestHintBtn.addEventListener('click', requestNextHint);
  }

  // ── Assistance Panel Tabs Controller ────────────────────────────────────────

  function switchTab(activeTabName) {
    const tabs = [
      { name: 'question', btn: tabQuestion, panel: panelQuestion },
      { name: 'editor', btn: tabEditor, panel: null },
      { name: 'hints', btn: tabHints, panel: panelHints },
      { name: 'assistant', btn: tabAssistant, panel: panelAssistant },
      { name: 'instructions', btn: tabInstructions, panel: panelInstructions },
    ];

    tabs.forEach(t => {
      if (!t.btn) return;
      if (t.name === activeTabName) {
        t.btn.classList.add('active');
        t.btn.setAttribute('aria-selected', 'true');
        t.btn.setAttribute('tabindex', '0');
        if (t.panel) {
          t.panel.classList.remove('hidden');
          t.panel.classList.add('active');
          if (window.anime) {
            window.anime({
              targets: t.panel,
              opacity: [0.75, 1],
              translateY: [6, 0],
              duration: 200,
              easing: 'easeOutQuad',
            });
          }
        }
      } else {
        t.btn.classList.remove('active');
        t.btn.setAttribute('aria-selected', 'false');
        t.btn.setAttribute('tabindex', '-1');
        if (t.panel) {
          t.panel.classList.remove('active');
          t.panel.classList.add('hidden');
        }
      }
    });

    if (activeTabName === 'editor') {
      if (panelQuestion) {
        panelQuestion.classList.remove('hidden');
        panelQuestion.classList.add('active');
      }
      if (editor) {
        editor.focus();
        editor.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }

  // ── Progressive Hints Controller ───────────────────────────────────────────

  function renderHintsUI(unlockedHints = []) {
    if (!hintsList) return;
    hintsList.innerHTML = '';

    const count = unlockedHints.length;
    if (hintsProgressPill) {
      hintsProgressPill.textContent = `${count} of 3 Unlocked`;
    }

    if (hintsTabBadge) {
      hintsTabBadge.textContent = `${count}/3`;
      if (count > 0) {
        hintsTabBadge.classList.remove('hidden');
      } else {
        hintsTabBadge.classList.add('hidden');
      }
    }

    if (hintsEmpty) {
      if (count > 0) {
        hintsEmpty.classList.add('hidden');
      } else {
        hintsEmpty.classList.remove('hidden');
      }
    }

    unlockedHints.forEach(h => {
      const card = document.createElement('div');
      const idx = h.hint_index || 1;
      const stage = (h.stage || 'Think').toLowerCase();
      let stageClass = 'stage-think';
      let pillClass = 'pill-think';
      if (stage.includes('investigate')) {
        stageClass = 'stage-investigate';
        pillClass = 'pill-investigate';
      } else if (stage.includes('narrow')) {
        stageClass = 'stage-narrow';
        pillClass = 'pill-narrow';
      }

      card.className = `hint-card ${stageClass}`;
      
      const label = h.label || `Hint ${idx} — ${h.stage || 'Think'}`;
      let timeStr = '';
      if (h.requested_at) {
        try {
          const d = new Date(h.requested_at);
          timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch (e) {}
      }

      const formattedText = formatHintText(h.hint_text || h.hint || '');

      card.innerHTML = `
        <div class="hint-card-header">
          <span class="hint-stage-pill ${pillClass}">${escapeHtml(label)}</span>
          ${timeStr ? `<span class="hint-time-pill">${escapeHtml(timeStr)}</span>` : ''}
        </div>
        <div class="hint-text">${formattedText}</div>
      `;
      hintsList.appendChild(card);
    });

    // Update button text, exhausted card, and button visibility
    if (requestHintBtn && hintsExhausted) {
      if (count >= 3) {
        requestHintBtn.classList.add('hidden');
        hintsExhausted.classList.remove('hidden');
      } else {
        requestHintBtn.classList.remove('hidden');
        hintsExhausted.classList.add('hidden');
        const nextIdx = count + 1;
        const nextStages = ['Think', 'Investigate', 'Narrow it down'];
        const nextStage = nextStages[nextIdx - 1];
        if (hintsBtnText) {
          if (count === 0) {
            hintsBtnText.textContent = 'Request First Hint (Hint 1 — Think)';
          } else {
            hintsBtnText.textContent = `Request Next Hint (Hint ${nextIdx} — ${nextStage})`;
          }
        }
      }
    }
  }

  function formatHintText(text) {
    if (!text) return '';
    const escaped = escapeHtml(text);
    return escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
  }

  async function requestNextHint() {
    if (!currentAttempt || isFinalized) return;

    if (hintsError) hintsError.classList.add('hidden');
    if (hintsLoading) hintsLoading.classList.remove('hidden');
    if (requestHintBtn) requestHintBtn.disabled = true;

    try {
      const res = await fetch('/api/hint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          attempt_id: currentAttempt.attempt_id,
          challenge_id: currentAttempt.challenge_id,
          learner_id: currentAttempt.learner_id,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (hintsError) {
          hintsError.textContent = err.detail || `Failed to retrieve hint (${res.status}).`;
          hintsError.classList.remove('hidden');
        }
        return;
      }

      const data = await res.json();
      if (data.unlocked_hints) {
        currentAttempt.unlocked_hints = data.unlocked_hints;
      } else if (data.status === 'active') {
        currentAttempt.unlocked_hints = currentAttempt.unlocked_hints || [];
        currentAttempt.unlocked_hints.push({
          hint_index: data.hint_number,
          stage: data.stage,
          label: data.label,
          hint_text: data.hint,
          requested_at: new Date().toISOString(),
        });
      }
      renderHintsUI(currentAttempt.unlocked_hints || []);
    } catch (err) {
      if (hintsError) {
        hintsError.textContent = `Network error while retrieving hint: ${err.message}`;
        hintsError.classList.remove('hidden');
      }
    } finally {
      if (hintsLoading) hintsLoading.classList.add('hidden');
      if (requestHintBtn) requestHintBtn.disabled = false;
    }
  }

  // ── AI Exam Assistant Controller ──────────────────────────────────────────

  function setupExamAssistant() {
    if (!assistantForm) return;

    // Character counter
    if (assistantInput && assistantCharCount) {
      assistantInput.addEventListener('input', () => {
        const len = assistantInput.value.length;
        assistantCharCount.textContent = len;
        if (len >= 1900) {
          assistantCharCount.style.color = '#ef4444';
        } else {
          assistantCharCount.style.color = '';
        }
      });

      // Submit on Enter key (Shift+Enter for newline)
      assistantInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          if (!assistantSendBtn.disabled) {
            assistantForm.dispatchEvent(new Event('submit', { cancelable: true }));
          }
        }
      });
    }

    // Suggested question pills
    if (assistantSuggestedPills) {
      assistantSuggestedPills.addEventListener('click', e => {
        const pill = e.target.closest('.suggested-pill');
        if (!pill || pill.disabled || isFinalized) return;
        const promptText = pill.getAttribute('data-prompt');
        if (promptText && assistantInput) {
          assistantInput.value = promptText;
          if (assistantCharCount) {
            assistantCharCount.textContent = promptText.length;
          }
          assistantInput.focus();
          if (window.anime) {
            window.anime({
              targets: pill,
              scale: [0.93, 1],
              duration: 180,
              easing: 'easeOutQuad',
            });
          }
        }
      });
    }

    // Form submission
    assistantForm.addEventListener('submit', async e => {
      e.preventDefault();
      await sendAssistantMessage();
    });
  }

  async function sendAssistantMessage() {
    if (!currentAttempt || isFinalized) return;

    const message = (assistantInput.value || '').trim();
    if (!message) return;

    if (assistantError) assistantError.classList.add('hidden');
    if (assistantLoading) assistantLoading.classList.remove('hidden');
    if (assistantSendBtn) assistantSendBtn.disabled = true;
    if (assistantInput) assistantInput.disabled = true;

    // Append user message bubble to conversation
    appendChatMessage('user', message);
    assistantInput.value = '';
    if (assistantCharCount) assistantCharCount.textContent = '0';

    try {
      const payload = {
        attempt_id: currentAttempt.attempt_id,
        message: message,
        current_code: editor ? editor.value : '',
        test_results_summary: lastVisibleTestSummary || null,
      };

      const res = await fetch('/api/exam/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const errorDetail = err.detail || `Assistant request failed (${res.status}).`;

        if (res.status === 400 && errorDetail.toLowerCase().includes('finalized')) {
          appendChatMessage('ai', 'This examination has already been finalized. AI Assistant is disabled.', false, false);
          disableAssistantUI();
        } else if (res.status === 400 && errorDetail.toLowerCase().includes('expired')) {
          appendChatMessage('ai', 'Examination time has expired. AI Assistant is disabled.', false, false);
          disableAssistantUI();
        } else {
          if (assistantError) {
            assistantError.textContent = errorDetail;
            assistantError.classList.remove('hidden');
          } else {
            appendChatMessage('ai', `⚠️ ${errorDetail}`, false, false);
          }
        }
        return;
      }

      const data = await res.json();
      const isRefusal = Boolean(data.guardrail_refusal || !data.guardrail_passed);
      appendChatMessage('ai', data.message, isRefusal, true);

    } catch (err) {
      if (assistantError) {
        assistantError.textContent = `Network / connection error: ${err.message}`;
        assistantError.classList.remove('hidden');
      }
    } finally {
      if (assistantLoading) assistantLoading.classList.add('hidden');
      if (!isFinalized) {
        if (assistantInput) {
          assistantInput.disabled = false;
          assistantInput.focus();
        }
        if (assistantSendBtn) assistantSendBtn.disabled = false;
      }
    }
  }

  function appendChatMessage(role, text, isRefusal = false, animate = true) {
    if (!assistantMessages) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = `assistant-msg ${role === 'user' ? 'msg--user' : 'msg--ai'}`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'msg-avatar';
    avatarDiv.textContent = role === 'user' ? '👤' : '🤖';

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'msg-bubble';

    if (isRefusal) {
      const refusalBadge = document.createElement('div');
      refusalBadge.className = 'assistant-refusal-badge';
      refusalBadge.innerHTML = '<span>🛡️</span> <span>Policy Refusal: Direct Solution Withheld</span>';
      bubbleDiv.appendChild(refusalBadge);
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content-formatted';
    contentDiv.innerHTML = formatAssistantMarkdown(text);
    bubbleDiv.appendChild(contentDiv);

    msgDiv.appendChild(avatarDiv);
    msgDiv.appendChild(bubbleDiv);
    assistantMessages.appendChild(msgDiv);

    // Scroll to latest message
    assistantMessages.scrollTop = assistantMessages.scrollHeight;

    if (animate && window.anime) {
      window.anime({
        targets: msgDiv,
        opacity: [0, 1],
        translateY: [8, 0],
        duration: 220,
        easing: 'easeOutQuad',
      });
    }
  }

  function formatAssistantMarkdown(text) {
    if (!text) return '';
    let escaped = escapeHtml(text);

    // Code blocks ```python ... ``` or ``` ... ```
    escaped = escaped.replace(/```(?:python)?\n([\s\S]*?)```/g, (match, code) => {
      return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code `...`
    escaped = escaped.replace(/`([^`\n]+)`/g, '<code>$1</code>');

    // Bold **...**
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Paragraphs / double linebreaks
    const paragraphs = escaped.split(/\n{2,}/);
    return paragraphs.map(p => {
      const trimmed = p.trim();
      if (!trimmed) return '';
      if (trimmed.startsWith('<pre>')) return trimmed;
      return `<p>${trimmed.replace(/\n/g, '<br>')}</p>`;
    }).join('');
  }

  function disableAssistantUI() {
    if (assistantInput) {
      assistantInput.disabled = true;
      assistantInput.placeholder = 'Examination closed. AI Assistant is disabled.';
    }
    if (assistantSendBtn) assistantSendBtn.disabled = true;
    if (assistantSuggestedPills) {
      const pills = assistantSuggestedPills.querySelectorAll('.suggested-pill');
      pills.forEach(p => (p.disabled = true));
    }
  }

  // ── Code Execution ─────────────────────────────────────────────────────────

  async function runVisibleTests() {
    if (!currentAttempt || isFinalized) return;

    const code = editor.value;
    if (!code.trim()) {
      showToast('Cannot run empty code.', 'warning');
      return;
    }

    setRunningState(true);
    consoleBadge.textContent = 'Executing in Docker sandbox…';
    consoleBadge.className = 'badge badge--checking';
    consoleOutput.innerHTML = '<div class="console-placeholder">Executing visible tests in isolated container…</div>';

    try {
      const res = await fetch(`/api/exam/${encodeURIComponent(currentAttempt.attempt_id)}/run-tests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        renderConsoleError(err.detail || `Test execution failed (${res.status}).`);
        return;
      }

      const data = await res.json();
      renderVisibleTestResults(data);
    } catch (err) {
      renderConsoleError(`Infrastructure / Network error during test run: ${err.message}`);
    } finally {
      setRunningState(false);
    }
  }

  async function finalizeExamSubmission() {
    if (!currentAttempt || isFinalized) return;

    const code = editor.value;
    setRunningState(true);
    consoleBadge.textContent = 'Submitting & Evaluating…';
    consoleBadge.className = 'badge badge--checking';
    consoleOutput.innerHTML = '<div class="console-placeholder">Running full evaluation inside disposable Docker sandbox…</div>';

    try {
      const res = await fetch(`/api/exam/${encodeURIComponent(currentAttempt.attempt_id)}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        renderConsoleError(err.detail || `Submission failed (${res.status}).`);
        return;
      }

      const data = await res.json();
      finalizeUIState(data.status, data);
    } catch (err) {
      renderConsoleError(`Infrastructure error during final submission: ${err.message}`);
    } finally {
      setRunningState(false);
    }
  }

  function setRunningState(isRunning) {
    runTestsBtn.disabled = isRunning;
    submitExamBtn.disabled = isRunning;
    headerSubmitBtn.disabled = isRunning;
    codeStatus.textContent = isRunning ? 'Executing…' : 'Ready';
  }

  function renderVisibleTestResults(data) {
    const passed = data.visible_passed;
    const total = data.visible_total;
    const allPassed = passed === total;

    lastVisibleTestSummary = `Visible Tests: ${passed}/${total} passed.` +
      (data.visible_tests || []).filter(t => t.outcome !== 'passed').map(t => `\n- ${t.label}: Expected ${t.expected}, Actual ${t.actual}`).join('');

    consoleBadge.textContent = `${passed}/${total} Visible Tests Passed`;
    consoleBadge.className = `badge ${allPassed ? 'badge--passed' : 'badge--failed'}`;

    let html = `<div style="margin-bottom: 12px; font-weight: 600; color: ${allPassed ? '#4ade80' : '#f87171'};">
      Visible Test Results: ${passed} of ${total} passed
    </div>`;

    (data.visible_tests || []).forEach(t => {
      const isPass = t.outcome === 'passed';
      const outcomeClass = isPass ? 'outcome-passed' : 'outcome-failed';

      html += `
        <div class="test-result-item">
          <div class="test-result-header">
            <strong>${escapeHtml(t.label)}</strong>
            <span class="${outcomeClass}">${escapeHtml(t.outcome.toUpperCase())}</span>
          </div>
          <div class="test-result-details">
            <span>Call:</span><code>${escapeHtml(t.call)}</code>
            <span>Expected:</span><code>${escapeHtml(t.expected)}</code>
            <span>Actual:</span><code>${escapeHtml(t.actual || 'None')}</code>
          </div>
        </div>
      `;
    });

    consoleOutput.innerHTML = html;
  }

  function finalizeUIState(status, results) {
    isFinalized = true;
    clearInterval(timerInterval);
    updateStatusBadge(status);
    editor.disabled = true;
    runTestsBtn.disabled = true;
    submitExamBtn.disabled = true;
    headerSubmitBtn.disabled = true;
    headerSubmitBtn.textContent = 'Submitted';
    resetBtn.disabled = true;
    if (requestHintBtn) requestHintBtn.disabled = true;
    disableAssistantUI();

    // Also update the console for users who view it underneath
    if (results) {
      const allPassed = results.all_passed;
      consoleBadge.textContent = allPassed ? 'Examination Passed' : 'Examination Complete';
      consoleBadge.className = `badge ${allPassed ? 'badge--passed' : 'badge--failed'}`;
      consoleOutput.innerHTML = '<div class="console-placeholder">Examination results are displayed in the results panel above.</div>';
    } else {
      consoleOutput.innerHTML = '<div class="console-placeholder">This examination attempt has been finalized.</div>';
    }

    // Show the dedicated results overlay
    showResultsScreen(status, results);
  }

  // ── Results Screen ──────────────────────────────────────────────────────

  function showResultsScreen(status, results) {
    const overlay = document.getElementById('exam-results-overlay');
    if (!overlay) return;

    // -- Header
    const statusIcon = document.getElementById('results-status-icon');
    const heading = document.getElementById('results-heading');
    const statusBdg = document.getElementById('results-status-badge');

    if (status === 'expired') {
      statusIcon.textContent = '⏰';
      statusIcon.className = 'results-status-icon icon-expired';
      heading.textContent = 'Time Expired';
      statusBdg.textContent = 'TIME EXPIRED';
      statusBdg.className = 'badge badge--status badge--expired';
    } else if (results && results.all_passed) {
      statusIcon.textContent = '✓';
      statusIcon.className = 'results-status-icon icon-passed';
      heading.textContent = 'Examination Passed';
      statusBdg.textContent = 'SUBMITTED';
      statusBdg.className = 'badge badge--status badge--submitted';
    } else {
      statusIcon.textContent = '✕';
      statusIcon.className = 'results-status-icon icon-failed';
      heading.textContent = 'Examination Complete';
      statusBdg.textContent = 'SUBMITTED';
      statusBdg.className = 'badge badge--status badge--submitted';
    }

    // -- Challenge Info
    const chTitle = document.getElementById('results-challenge-title');
    const diffBdg = document.getElementById('results-difficulty-badge');
    if (currentAttempt && currentAttempt.challenge) {
      chTitle.textContent = currentAttempt.challenge.title;
      const diff = currentAttempt.challenge.difficulty || 'easy';
      diffBdg.textContent = diff.toUpperCase();
      diffBdg.className = `badge badge--difficulty difficulty ${diff}`;
    }

    // -- Score Card
    const visScore = document.getElementById('results-visible-score');
    const hidScore = document.getElementById('results-hidden-score');
    const totalScore = document.getElementById('results-total-score');

    if (results && results.visible_tests) {
      const visPassed = results.visible_tests.filter(t => t.outcome === 'passed').length;
      const visTotal = results.visible_tests.length;
      visScore.textContent = `${visPassed} / ${visTotal} passed`;
      visScore.className = `results-score-value ${visPassed === visTotal ? 'score-passed' : 'score-failed'}`;
    } else if (status === 'expired') {
      visScore.textContent = 'Not Evaluated';
      visScore.className = 'results-score-value';
    }

    if (results && results.hidden_summary) {
      const hp = results.hidden_summary.passed;
      const ht = results.hidden_summary.total;
      hidScore.textContent = `${hp} / ${ht} passed`;
      hidScore.className = `results-score-value ${hp === ht ? 'score-passed' : 'score-failed'}`;
    } else if (status === 'expired') {
      hidScore.textContent = 'Not Evaluated';
      hidScore.className = 'results-score-value';
    }

    if (results && typeof results.all_passed === 'boolean') {
      const allPassed = results.all_passed;
      totalScore.textContent = allPassed ? '✓ All Tests Passed' : '✕ Some Tests Failed';
      totalScore.className = `results-score-value ${allPassed ? 'score-passed' : 'score-failed'}`;
    } else if (status === 'expired') {
      totalScore.textContent = '⏰ Time Expired';
      totalScore.className = 'results-score-value score-failed';
    }

    // -- Summary
    const summaryEl = document.getElementById('results-summary-text');
    if (results && results.summary) {
      summaryEl.textContent = results.summary;
    } else if (status === 'expired') {
      summaryEl.textContent = 'Examination time has expired. This attempt has been finalized.';
    } else {
      summaryEl.textContent = 'This examination attempt has been finalized.';
    }

    // -- Timestamp
    const tsEl = document.getElementById('results-timestamp-value');
    const ts = (results && results.submitted_at) || (currentAttempt && currentAttempt.submitted_at);
    const prefix = status === 'expired' ? 'Expired' : 'Submitted';
    if (ts) {
      try {
        tsEl.textContent = `${prefix} at ${new Date(ts).toLocaleString()}`;
      } catch (_) {
        tsEl.textContent = `${prefix} at ${new Date().toLocaleString()}`;
      }
    } else {
      tsEl.textContent = `${prefix} at ${new Date().toLocaleString()}`;
    }

    // -- Visible Test Results List
    const testList = document.getElementById('results-test-list');
    testList.innerHTML = '';
    if (results && results.visible_tests) {
      results.visible_tests.forEach(t => {
        const isPass = t.outcome === 'passed';
        const item = document.createElement('div');
        item.className = 'results-test-item';
        item.innerHTML = `
          <span class="test-label">${escapeHtml(t.label)}</span>
          <span class="test-outcome ${isPass ? 'outcome-pass' : 'outcome-fail'}">${escapeHtml(t.outcome.toUpperCase())}</span>
        `;
        testList.appendChild(item);
      });
    }

    // -- Button handlers
    const exitBtn = document.getElementById('results-exit-btn');
    const nextBtn = document.getElementById('results-next-btn');

    exitBtn.addEventListener('click', handleExitExam);
    nextBtn.addEventListener('click', handleNextChallenge);

    // Keyboard support
    exitBtn.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleExitExam(); } });
    nextBtn.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleNextChallenge(); } });

    // Show the overlay
    overlay.classList.remove('hidden');

    // Focus the Next Challenge button for keyboard navigation
    setTimeout(() => nextBtn.focus(), 100);

    // Preload next challenge in the background so "Next Challenge" switches immediately
    preloadNextChallenge();
  }

  // ── Navigation Handlers ─────────────────────────────────────────────────

  const CHALLENGES_URL = '/#challenges';

  function navigateToChallenges(hashSuffix) {
    const targetUrl = hashSuffix ? `/${hashSuffix}` : CHALLENGES_URL;

    // Try to communicate with the opener tab (the main Debug Dojo tab)
    if (window.opener && !window.opener.closed) {
      try {
        // Send a validated postMessage to the opener
        window.opener.postMessage({
          type: 'debug_dojo_exam_complete',
          action: 'navigate',
          target: hashSuffix || '#challenges',
          attemptId: currentAttempt ? currentAttempt.attempt_id : null,
        }, window.location.origin);

        try {
          window.opener.focus();
        } catch (_) {}
      } catch (e) {
        // opener inaccessible — fall through to direct navigation
      }
    }

    // Attempt to close this exam tab so the user returns cleanly to the opener tab
    try {
      window.close();
    } catch (_) {}

    // Fallback: navigate the current tab
    // (runs if window.close was prevented or ignored by the browser)
    setTimeout(() => {
      window.location.href = targetUrl;
    }, 100);
  }

  function handleExitExam() {
    navigateToChallenges('#challenges');
  }

  let preloadedNextChallengeId = null;

  async function preloadNextChallenge() {
    try {
      const learnerId = (currentAttempt && currentAttempt.learner_id) || 'student1';
      const currentChallengeId = currentAttempt ? currentAttempt.challenge_id : null;

      const [recRes, chalRes] = await Promise.all([
        fetch(`/api/learner/${encodeURIComponent(learnerId)}`).catch(() => null),
        fetch('/api/challenges').catch(() => null),
      ]);

      let allCh = [];
      if (chalRes && chalRes.ok) {
        allCh = await chalRes.json();
      }

      let passedSet = new Set();
      let backendRecId = null;

      if (recRes && recRes.ok) {
        const data = await recRes.json();
        passedSet = new Set((data.passed_challenges || []).map(c => String(c)));
        if (data.recommended_challenge && data.recommended_challenge.id) {
          backendRecId = data.recommended_challenge.id;
        }
      }

      if (currentAttempt && currentChallengeId) {
        passedSet.add(currentChallengeId);
        passedSet.add(currentChallengeId.replace(/-/g, '_'));
      }

      if (backendRecId && backendRecId !== currentChallengeId && !passedSet.has(backendRecId)) {
        preloadedNextChallengeId = backendRecId;
        return;
      }

      if (allCh && allCh.length > 0) {
        const curIdx = allCh.findIndex(c => c.id === currentChallengeId || c.id === (currentChallengeId && currentChallengeId.replace(/-/g, '_')));
        if (curIdx !== -1) {
          for (let i = curIdx + 1; i < allCh.length; i++) {
            if (!passedSet.has(allCh[i].id)) {
              preloadedNextChallengeId = allCh[i].id;
              return;
            }
          }
        }
        for (let i = 0; i < allCh.length; i++) {
          if (allCh[i].id !== currentChallengeId && !passedSet.has(allCh[i].id)) {
            preloadedNextChallengeId = allCh[i].id;
            return;
          }
        }
      }
    } catch (_) {}
  }

  async function handleNextChallenge() {
    const nextBtn = document.getElementById('results-next-btn');
    const completionMsg = document.getElementById('results-completion-msg');

    // 1. If next challenge was already preloaded, switch IMMEDIATELY!
    if (preloadedNextChallengeId) {
      const candidateId = preloadedNextChallengeId;
      if (window.opener && !window.opener.closed) {
        try {
          window.opener.postMessage({
            type: 'debug_dojo_exam_complete',
            action: 'navigate',
            target: `#challenges?highlight=${encodeURIComponent(candidateId)}`,
            challengeId: candidateId,
            attemptId: currentAttempt ? currentAttempt.attempt_id : null,
          }, window.location.origin);
        } catch (_) {}
      }
      const targetUrl = `/exam?challenge_id=${encodeURIComponent(candidateId)}`;
      window.location.href = targetUrl;
      return;
    }

    if (nextBtn) {
      nextBtn.disabled = true;
      nextBtn.textContent = 'Opening next challenge…';
    }

    try {
      const learnerId = (currentAttempt && currentAttempt.learner_id) || 'student1';
      const currentChallengeId = currentAttempt ? currentAttempt.challenge_id : null;

      // Fetch all challenges and learner data in parallel
      const [recRes, chalRes] = await Promise.all([
        fetch(`/api/learner/${encodeURIComponent(learnerId)}`).catch(() => null),
        fetch('/api/challenges').catch(() => null),
      ]);

      let allCh = [];
      if (chalRes && chalRes.ok) {
        allCh = await chalRes.json();
      }

      let passedSet = new Set();
      let backendRecId = null;

      if (recRes && recRes.ok) {
        const data = await recRes.json();
        passedSet = new Set((data.passed_challenges || []).map(c => String(c)));
        if (data.recommended_challenge && data.recommended_challenge.id) {
          backendRecId = data.recommended_challenge.id;
        }
      }

      // If current exam was submitted, treat current challenge as completed
      if (currentAttempt && currentChallengeId) {
        passedSet.add(currentChallengeId);
        passedSet.add(currentChallengeId.replace(/-/g, '_'));
      }

      let candidateId = null;
      if (backendRecId && backendRecId !== currentChallengeId && !passedSet.has(backendRecId)) {
        candidateId = backendRecId;
      } else if (allCh && allCh.length > 0) {
        const curIdx = allCh.findIndex(c => c.id === currentChallengeId || c.id === (currentChallengeId && currentChallengeId.replace(/-/g, '_')));

        let candidate = null;
        if (curIdx !== -1) {
          for (let i = curIdx + 1; i < allCh.length; i++) {
            if (!passedSet.has(allCh[i].id)) {
              candidate = allCh[i];
              break;
            }
          }
        }

        if (!candidate) {
          for (let i = 0; i < allCh.length; i++) {
            if (allCh[i].id !== currentChallengeId && !passedSet.has(allCh[i].id)) {
              candidate = allCh[i];
              break;
            }
          }
        }

        if (candidate) {
          candidateId = candidate.id;
        }
      }

      if (candidateId) {
        if (window.opener && !window.opener.closed) {
          try {
            window.opener.postMessage({
              type: 'debug_dojo_exam_complete',
              action: 'navigate',
              target: `#challenges?highlight=${encodeURIComponent(candidateId)}`,
              challengeId: candidateId,
              attemptId: currentAttempt ? currentAttempt.attempt_id : null,
            }, window.location.origin);
          } catch (_) {}
        }

        // Immediately switch this tab to the corresponding challenge exam!
        const targetUrl = `/exam?challenge_id=${encodeURIComponent(candidateId)}`;
        window.location.href = targetUrl;
        return;
      }

      // All challenges in the catalogue have been completed!
      showCompletionMessage(completionMsg, nextBtn);
      return;
    } catch (e) {
      // Graceful fallback
    } finally {
      if (nextBtn && nextBtn.textContent === 'Opening next challenge…') {
        nextBtn.disabled = false;
        nextBtn.textContent = 'Next Challenge →';
      }
    }

    // Default fallback to challenges catalogue
    const targetUrl = CHALLENGES_URL;
    window.location.href = targetUrl;
  }

  function showCompletionMessage(msgEl, btn) {
    if (msgEl) {
      msgEl.innerHTML = `<span class="completion-highlight">🎉 You've reached the end of the available challenges!</span><br>Explore the full catalogue to review or re-attempt any challenge.`;
      msgEl.classList.remove('hidden');
    }
    if (btn) {
      btn.textContent = 'View All Challenges';
      btn.disabled = false;
      btn.replaceWith(btn.cloneNode(true));
      const newBtn = document.getElementById('results-next-btn');
      if (newBtn) {
        newBtn.addEventListener('click', () => navigateToChallenges('#challenges'));
      }
    }
  }

  function renderConsoleError(errorText) {
    consoleBadge.textContent = 'Execution Error';
    consoleBadge.className = 'badge badge--failed';
    consoleOutput.innerHTML = `
      <div style="color: #f87171; background-color: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; border-radius: 6px; padding: 12px;">
        <strong>Error:</strong> ${escapeHtml(errorText)}
      </div>
    `;
  }

  function updateStatusBadge(status) {
    statusBadge.textContent = (status || 'in_progress').replace('_', ' ').toUpperCase();
    statusBadge.className = 'badge badge--status';
    if (status === 'submitted') {
      statusBadge.classList.add('badge--submitted');
    } else if (status === 'expired') {
      statusBadge.classList.add('badge--expired');
    } else {
      statusBadge.classList.add('badge--in-progress');
    }
  }

  function renderErrorScreen(message, challengeId) {
    const restartBtn = challengeId
      ? `<a href="/exam?challenge_id=${encodeURIComponent(challengeId)}" style="background-color: #10b981; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">🎓 Start Fresh Exam</a>`
      : '';
    document.body.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background-color: #0b0f19; color: #f8fafc; font-family: sans-serif; padding: 24px; text-align: center;">
        <h1 style="font-size: 2rem; color: #f87171; margin-bottom: 12px;">⚠️ Examination Notice</h1>
        <p style="font-size: 1.1rem; color: #cbd5e1; max-width: 520px; line-height: 1.5; margin-bottom: 24px;">${escapeHtml(message)}</p>
        <div style="display: flex; gap: 12px; flex-wrap: wrap; justify-content: center;">
          ${restartBtn}
          <a href="/" style="background-color: #3b82f6; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Return to Debug Dojo</a>
        </div>
      </div>
    `;
  }

  // ── Utilities ──────────────────────────────────────────────────────────────

  function escapeHtml(str) {
    if (typeof str !== 'string') return String(str || '');
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatMarkdown(text) {
    let out = escapeHtml(text);
    // Bold
    out = out.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Code inline
    out = out.replace(/`(.*?)`/g, '<code>$1</code>');
    // Paragraphs
    out = out.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br/>')}</p>`).join('');
    return out;
  }

})();

