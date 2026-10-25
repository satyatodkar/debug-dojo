/* ============================================================
   Debug Dojo — app.js (Phase 6 Polish)
   Complete, beginner-friendly learning experience:
     1. Health check & status monitoring
     2. Challenge catalogue with live filtering & mobile drawer
     3. Code editor with work preservation & Tab indentation
     4. Restricted execution & clear infrastructure vs learner error states
     5. Progressive 3-tier hints ladder
     6. Persistent Learner Progress & Concept Mastery Dashboard
     7. Keyboard accessibility & responsive view navigation
   ============================================================ */

// ---------------------------------------------------------------------------
// State variables
// ---------------------------------------------------------------------------

let activeId = null;
let currentChallenge = null;
let activeSubmissionId = null;
let currentLearnerId = 'student1';
let isSubmitting = false;

// Authentication & Session state
let currentUser = null;
let redirectAfterLogin = null;

// Challenge data caches for work preservation
let allChallenges = [];
const learnerCodeCache = {};
const originalStarterCodeCache = {};

// ---------------------------------------------------------------------------
// 1. Health check
// ---------------------------------------------------------------------------

async function checkHealth() {
  const badge  = document.getElementById('health-badge');
  const detail = document.getElementById('status-detail');

  try {
    const response = await fetch('/api/health');

    if (response.ok) {
      const data = await response.json();
      if (data.status === 'ok') {
        badge.textContent = '✓ Connected';
        badge.className   = 'badge badge--ok';
        if (detail) detail.textContent = 'Backend healthy — GET /api/health returned {"status":"ok"}';
      } else {
        badge.textContent = '⚠ Unexpected';
        badge.className   = 'badge badge--error';
      }
    } else {
      badge.textContent = '✗ HTTP ' + response.status;
      badge.className   = 'badge badge--error';
    }
  } catch (err) {
    badge.textContent = '✗ No connection';
    badge.className   = 'badge badge--error';
    if (detail) detail.textContent = 'Cannot reach backend. Error: ' + err.message;
  }
}

// ---------------------------------------------------------------------------
// 2. Anime.js Animation Module (Subtle, Restrained, Accessible)
// ---------------------------------------------------------------------------

function isReducedMotion() {
  return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function animateViewTransition(viewEl) {
  if (isReducedMotion() || !window.anime || !viewEl) return;
  try {
    anime.remove(viewEl);
    anime({
      targets: viewEl,
      opacity: [0, 1],
      translateY: [4, 0],
      duration: 220,
      easing: 'easeOutQuad',
    });
  } catch (_) {}
}

function animateLanding() {
  if (isReducedMotion() || !window.anime) return;
  try {
    anime.remove(['.hero-headline', '.hero-sub', '.hero-cta-group', '.feature-card', '.step-card']);
    anime({
      targets: ['.hero-headline', '.hero-sub', '.hero-cta-group'],
      opacity: [0, 1],
      translateY: [12, 0],
      delay: anime.stagger(90),
      duration: 550,
      easing: 'easeOutCubic',
    });
    anime({
      targets: '.feature-card',
      opacity: [0, 1],
      translateY: [14, 0],
      delay: anime.stagger(80, { start: 200 }),
      duration: 500,
      easing: 'easeOutCubic',
    });
  } catch (_) {}
}

function animateHome() {
  if (isReducedMotion() || !window.anime) return;
  try {
    anime.remove(['.home-welcome-card', '.home-card']);
    anime({
      targets: '.home-welcome-card',
      opacity: [0, 1],
      translateY: [8, 0],
      duration: 400,
      easing: 'easeOutQuad',
    });
    anime({
      targets: '.home-card',
      opacity: [0, 1],
      translateY: [12, 0],
      delay: anime.stagger(70, { start: 120 }),
      duration: 450,
      easing: 'easeOutCubic',
    });
  } catch (_) {}
}

function animateDashboard() {
  if (isReducedMotion() || !window.anime) return;
  try {
    anime.remove(['.full-width-card', '.stat-pill', '.mistake-card-item']);
    anime({
      targets: '.stat-pill',
      scale: [0.96, 1],
      opacity: [0, 1],
      delay: anime.stagger(50),
      duration: 380,
      easing: 'easeOutBack',
    });
    anime({
      targets: '.full-width-card',
      opacity: [0, 1],
      translateY: [10, 0],
      delay: anime.stagger(80, { start: 100 }),
      duration: 450,
      easing: 'easeOutCubic',
    });
  } catch (_) {}
}

function animateResultsTable() {
  if (isReducedMotion() || !window.anime) return;
  try {
    anime.remove('.test-results-table tbody tr');
    anime({
      targets: '.test-results-table tbody tr',
      opacity: [0, 1],
      translateX: [-6, 0],
      delay: anime.stagger(45),
      duration: 320,
      easing: 'easeOutQuad',
    });
  } catch (_) {}
}

function animateMasteryBars() {
  if (isReducedMotion() || !window.anime) return;
  try {
    const fills = document.querySelectorAll('.mastery-item .progress-fill');
    if (!fills.length) return;
    fills.forEach(fill => {
      const targetW = fill.getAttribute('data-target-width') || fill.style.width || '0%';
      anime({
        targets: fill,
        width: ['0%', targetW],
        duration: 700,
        easing: 'easeOutCubic',
      });
    });
  } catch (_) {}
}

function selectAndOpenChallenge(challengeId) {
  if (!challengeId) return;
  const cleanId = challengeId.replace(/-/g, '_');
  const idx = allChallenges.findIndex(c => c.id === cleanId);
  loadChallengeDetail(cleanId, idx >= 0 ? idx + 1 : 1);
  showView('workspace');
}

// ---------------------------------------------------------------------------
// 3. Navigation & View Switching
// ---------------------------------------------------------------------------

const VALID_VIEWS = ['home', 'landing', 'challenges', 'workspace', 'dashboard', 'login', 'signup', 'account'];

function showView(viewName) {
  if (!viewName) return;
  let cleanName = String(viewName).trim().toLowerCase().replace(/^view-/, '');

  // Alias landing to home so both point to the unified shared homepage
  if (cleanName === 'landing') {
    cleanName = 'home';
  }

  // Validate view names before switching
  if (!VALID_VIEWS.includes(cleanName)) {
    console.warn(`[Debug Dojo] Invalid view name requested: "${viewName}". Must be one of: ${VALID_VIEWS.join(', ')}`);
    return;
  }

  // Navigation Guard: Protect private workspace, dashboard and account views
  if (['workspace', 'dashboard', 'account'].includes(cleanName) && !currentUser) {
    redirectAfterLogin = cleanName;
    showAuthAlert('login-alert', 'Please log in or create an account to access this page.', 'error');
    showView('login');
    return;
  }

  // Preserve current code editor contents in cache when navigating between views
  const editor = document.getElementById('starter-code');
  if (activeId && editor) {
    learnerCodeCache[activeId] = editor.value;
  }

  // Hide all views
  const allViews = document.querySelectorAll('.view');
  allViews.forEach(v => {
    v.classList.add('hidden');
  });

  // Reveal the requested view
  const targetView = document.getElementById(`view-${cleanName}`);
  if (targetView) {
    targetView.classList.remove('hidden');
    animateViewTransition(targetView);
  }

  // Update navigation active state and accessible attributes
  const navTabs = document.querySelectorAll('.nav-tabs .nav-tab[data-view]');
  navTabs.forEach(tab => {
    const isTarget = tab.dataset.view === cleanName || (cleanName === 'home' && tab.dataset.view === 'landing');
    tab.classList.toggle('active', isTarget);
    tab.setAttribute('aria-selected', isTarget ? 'true' : 'false');
    tab.setAttribute('tabindex', isTarget ? '0' : '-1');
  });

  // View-specific data fetching & animation
  if (cleanName === 'account' && currentUser) {
    loadAccountData();
  } else if (cleanName === 'home') {
    if (currentUser) {
      loadHomeSummary(currentUser.user_id);
    }
    animateLanding();
  } else if (cleanName === 'dashboard') {
    loadLearnerDashboard(currentUser ? currentUser.user_id : currentLearnerId);
    animateDashboard();
  } else if (cleanName === 'challenges' && allChallenges.length === 0) {
    loadChallengeList();
  }

  // Sync URL history state smoothly
  try {
    const targetPath = (cleanName === 'home') ? '/' : `/${cleanName}`;
    if (window.location.pathname !== targetPath) {
      window.history.pushState({ view: cleanName }, '', targetPath);
    }
  } catch (_) {}
}

function switchView(target) {
  showView(target);
}

function toggleMobileSidebar() {
  const sidebar = document.getElementById('challenge-sidebar');
  if (sidebar) {
    sidebar.classList.toggle('mobile-hidden');
  }
}

// ---------------------------------------------------------------------------
// 3. Challenge List & Live Filtering
// ---------------------------------------------------------------------------

async function loadChallengeList() {
  const statusEl = document.getElementById('list-status');
  const listEl   = document.getElementById('challenge-list');
  const countEl  = document.getElementById('challenge-count');
  const mobCount = document.getElementById('mobile-challenge-count');

  try {
    const response = await fetch('/api/challenges');

    if (!response.ok) {
      statusEl.textContent = 'Failed to load challenges (HTTP ' + response.status + ').';
      return;
    }

    allChallenges = await response.json();
    if (!currentChallenge && allChallenges.length > 0) {
      currentChallenge = allChallenges[0];
    }

    statusEl.style.display = 'none';
    if (countEl) countEl.textContent = allChallenges.length;
    if (mobCount) mobCount.textContent = allChallenges.length;

    renderChallengeItems(allChallenges);
    renderChallengesCatalogue(allChallenges);

  } catch (err) {
    statusEl.textContent = 'Network error loading challenges: ' + err.message;
  }
}

function renderChallengesCatalogue(challenges) {
  const gridEl = document.getElementById('challenges-grid');
  if (!gridEl) return;
  gridEl.innerHTML = '';

  if (!challenges || challenges.length === 0) {
    const emptyP = document.createElement('p');
    emptyP.className = 'sidebar-status';
    emptyP.textContent = 'No challenges available.';
    gridEl.appendChild(emptyP);
    return;
  }

  challenges.forEach((ch, index) => {
    const card = document.createElement('article');
    card.className = 'challenge-card';
    card.setAttribute('role', 'listitem');
    card.dataset.id = ch.id;

    // Header with challenge number and difficulty
    const header = document.createElement('div');
    header.className = 'challenge-card-header';

    const numSpan = document.createElement('span');
    numSpan.className = 'ci-num';
    numSpan.textContent = `#${index + 1}`;

    const diffSpan = document.createElement('span');
    diffSpan.className = `difficulty ${ch.difficulty}`;
    diffSpan.textContent = ch.difficulty.charAt(0).toUpperCase() + ch.difficulty.slice(1);

    header.append(numSpan, diffSpan);

    // Title
    const title = document.createElement('h3');
    title.className = 'challenge-card-title';
    title.textContent = ch.title;

    // Tags
    const tagsRow = document.createElement('div');
    tagsRow.className = 'tag-row';
    (ch.tags || []).forEach(tag => {
      const tagSpan = document.createElement('span');
      tagSpan.className = 'concept-tag';
      tagSpan.textContent = tag;
      tagsRow.appendChild(tagSpan);
    });

    // Description
    const desc = document.createElement('p');
    desc.className = 'challenge-card-desc';
    desc.textContent = ch.description;

    // Footer with "Solve Challenge" and "Start Exam" buttons
    const footer = document.createElement('div');
    footer.className = 'challenge-card-footer';
    footer.style.display = 'flex';
    footer.style.gap = '8px';
    footer.style.flexWrap = 'wrap';

    const solveBtn = document.createElement('button');
    solveBtn.className = 'btn btn--primary btn--sm solve-challenge-btn';
    solveBtn.textContent = 'Solve Challenge';
    solveBtn.dataset.id = ch.id;
    solveBtn.setAttribute('aria-label', `Solve Challenge: ${ch.title}`);

    solveBtn.addEventListener('click', () => {
      loadChallengeDetail(ch.id, index + 1);
      showView('workspace');
    });

    const examBtn = document.createElement('button');
    examBtn.className = 'btn btn--secondary btn--sm start-exam-btn';
    examBtn.textContent = '🎓 Start Exam';
    examBtn.dataset.id = ch.id;
    examBtn.title = 'Open this challenge in an official examination panel in a separate browser tab';
    examBtn.setAttribute('aria-label', `Start Exam for ${ch.title}`);

    let openingExam = false;
    examBtn.addEventListener('click', () => {
      if (openingExam) return;
      openingExam = true;
      openExamination(ch.id, examBtn, null);
      setTimeout(() => {
        openingExam = false;
      }, 1500);
    });

    footer.append(solveBtn, examBtn);
    card.append(header, title, tagsRow, desc, footer);
    gridEl.appendChild(card);
  });
}

function renderChallengeItems(challenges) {
  const listEl = document.getElementById('challenge-list');
  listEl.innerHTML = '';

  if (challenges.length === 0) {
    const emptyLi = document.createElement('li');
    emptyLi.className = 'sidebar-status';
    emptyLi.textContent = 'No challenges match your search.';
    listEl.appendChild(emptyLi);
    return;
  }

  challenges.forEach((ch, index) => {
    const li  = document.createElement('li');
    li.className = 'challenge-item';

    const btn = document.createElement('button');
    btn.setAttribute('aria-label', `Open challenge: ${ch.title}`);
    btn.dataset.id = ch.id;
    if (ch.id === activeId) {
      btn.classList.add('active');
    }

    const titleSpan = document.createElement('span');
    titleSpan.className   = 'ci-title';
    titleSpan.textContent = ch.title;

    const metaRow  = document.createElement('span');
    metaRow.className = 'ci-meta';

    const numSpan  = document.createElement('span');
    numSpan.className   = 'ci-num';
    numSpan.textContent = `#${index + 1}`;

    const diffSpan = document.createElement('span');
    diffSpan.className   = `difficulty ${ch.difficulty}`;
    diffSpan.textContent = ch.difficulty.charAt(0).toUpperCase() + ch.difficulty.slice(1);

    metaRow.append(numSpan, diffSpan);
    btn.append(titleSpan, metaRow);

    btn.addEventListener('click', () => {
      // Auto-close mobile sidebar if open
      const sidebar = document.getElementById('challenge-sidebar');
      if (sidebar && window.innerWidth <= 900) {
        sidebar.classList.add('mobile-hidden');
      }
      loadChallengeDetail(ch.id, index + 1);
    });

    li.appendChild(btn);
    listEl.appendChild(li);
  });
}

function filterChallenges(query) {
  const q = query.trim().toLowerCase();
  if (!q) {
    renderChallengeItems(allChallenges);
    return;
  }

  const filtered = allChallenges.filter(ch => {
    const titleMatch = ch.title.toLowerCase().includes(q);
    const diffMatch  = ch.difficulty.toLowerCase().includes(q);
    const tagMatch   = (ch.tags || []).some(t => t.toLowerCase().includes(q));
    return titleMatch || diffMatch || tagMatch;
  });

  renderChallengeItems(filtered);
}

// ---------------------------------------------------------------------------
// 4. Challenge Detail & Code Work Preservation
// ---------------------------------------------------------------------------

async function loadChallengeDetail(id, number) {
  // Save current challenge code before navigating away
  const editor = document.getElementById('starter-code');
  if (activeId && editor) {
    learnerCodeCache[activeId] = editor.value;
  }

  document.querySelectorAll('.challenge-item button').forEach(b => {
    b.classList.toggle('active', b.dataset.id === id);
  });

  const welcomeEl    = document.getElementById('welcome-msg');
  const detailEl     = document.getElementById('challenge-detail');
  const resultsBox   = document.getElementById('test-results');
  const runBtn       = document.getElementById('run-btn');
  const hintsSection = document.getElementById('hints-section');

  if (welcomeEl) welcomeEl.style.display = 'none';
  if (detailEl)  detailEl.classList.remove('hidden');

  // Reset hints UI for new challenge view
  activeSubmissionId = null;
  if (hintsSection) hintsSection.classList.add('hidden');

  resultsBox.innerHTML =
    '<p class="not-implemented">Ready. Click <strong>Run Tests</strong> to evaluate your solution in the Docker sandbox.</p>';
  runBtn.disabled = false;

  try {
    const response = await fetch(`/api/challenges/${id}`);

    if (!response.ok) {
      detailEl.innerHTML =
        `<p class="not-implemented" style="padding:1rem">
           Error loading challenge (HTTP ${response.status}). Please refresh the page.
         </p>`;
      return;
    }

    const ch = await response.json();
    activeId = id;
    currentChallenge = ch;

    // Cache original starter code for Reset functionality
    originalStarterCodeCache[id] = ch.starter_code;

    // Header info
    const numEl = document.getElementById('d-number');
    if (numEl) numEl.textContent = number ? `Challenge #${number}` : `Challenge`;

    document.getElementById('d-title').textContent = ch.title;
    document.getElementById('d-desc').textContent  = ch.description;

    const diffEl = document.getElementById('d-difficulty');
    diffEl.textContent = ch.difficulty.charAt(0).toUpperCase() + ch.difficulty.slice(1);
    diffEl.className   = `difficulty ${ch.difficulty}`;

    const tagsEl = document.getElementById('d-tags');
    tagsEl.innerHTML = '';
    (ch.tags || []).forEach(tag => {
      const pill = document.createElement('span');
      pill.className   = 'concept-tag';
      pill.textContent = tag;
      tagsEl.appendChild(pill);
    });

    // Work preservation: Restore previously edited code or fallback to starter code
    if (learnerCodeCache[id] !== undefined) {
      editor.value = learnerCodeCache[id];
    } else {
      editor.value = ch.starter_code;
    }

    // Populate visible test cases table
    const tbody = document.getElementById('tests-body');
    tbody.innerHTML = '';
    ch.visible_tests.forEach((test, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML =
        `<td>${i + 1}</td>` +
        `<td>${escapeHtml(test.label)}</td>` +
        `<td><code>${escapeHtml(test.call)}</code></td>` +
        `<td><code>${escapeHtml(test.expected)}</code></td>`;
      tbody.appendChild(tr);
    });

    // Switch view to workspace and focus editor
    switchView('workspace');

  } catch (err) {
    detailEl.innerHTML =
      `<p class="not-implemented" style="padding:1rem">
         Network error: ${escapeHtml(err.message)}
       </p>`;
  }
}

function resetActiveChallengeCode() {
  if (!activeId || !originalStarterCodeCache[activeId]) return;
  const editor = document.getElementById('starter-code');
  if (editor) {
    editor.value = originalStarterCodeCache[activeId];
    learnerCodeCache[activeId] = originalStarterCodeCache[activeId];
    editor.focus();
  }
}

// ---------------------------------------------------------------------------
// 5. Code Execution & Test Submission
// ---------------------------------------------------------------------------

async function submitCode() {
  if (!activeId || isSubmitting) return;

  const runBtn       = document.getElementById('run-btn');
  const runStatus    = document.getElementById('run-status');
  const resultsBox   = document.getElementById('test-results');
  const hintsSection = document.getElementById('hints-section');
  const code         = document.getElementById('starter-code').value;

  // Save current code to cache
  learnerCodeCache[activeId] = code;

  // Prevent duplicate submissions
  isSubmitting = true;
  runBtn.disabled = true;
  runBtn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Running tests…';
  runStatus.textContent = 'Executing tests in isolated Docker container…';
  resultsBox.innerHTML =
    '<p class="not-implemented"><span class="spinner" aria-hidden="true"></span> Executing tests in isolated Docker container. Please wait…</p>';

  if (hintsSection) hintsSection.classList.add('hidden');

  try {
    const response = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        learner_id: currentUser ? currentUser.user_id : currentLearnerId,
        challenge_id: activeId,
        code: code,
      }),
    });

    // Handle infrastructure / sandbox errors distinctly from student code bugs
    if (!response.ok) {
      let errorMsg = `Server error (HTTP ${response.status})`;
      try {
        const errJson = await response.json();
        if (errJson.detail) errorMsg = errJson.detail;
      } catch (_) {}

      // Distinct Infrastructure Error Banner
      resultsBox.innerHTML = `
        <div class="infra-error-card">
          <div class="infra-error-header">
            <span>⚙️ Execution Environment Alert</span>
          </div>
          <p class="infra-error-body">${escapeHtml(errorMsg)}</p>
          <span class="infra-error-subtext">This is a system/Docker environment status, not an error in your Python code logic.</span>
        </div>`;
      return;
    }

    const data = await response.json();
    activeSubmissionId = data.submission_id;

    // Render per-test outcomes table
    renderTestResults(data);

    // Refresh learner dashboard & home progress immediately
    const effUser = currentUser ? currentUser.user_id : currentLearnerId;
    loadLearnerDashboard(effUser);
    loadHomeDashboard(effUser);

    // Setup progressive hints if tests failed
    if (hintsSection) {
      if (!data.all_passed) {
        hintsSection.classList.remove('hidden');
        resetHintsUI();
      } else {
        hintsSection.classList.add('hidden');
      }
    }

  } catch (err) {
    // Network failure
    resultsBox.innerHTML = `
      <div class="infra-error-card">
        <div class="infra-error-header">
          <span>⚙️ Network Connection Alert</span>
        </div>
        <p class="infra-error-body">${escapeHtml(err.message)}</p>
        <span class="infra-error-subtext">Cannot reach the backend server. Verify the server is running on localhost:8000.</span>
      </div>`;
  } finally {
    isSubmitting = false;
    runBtn.disabled = false;
    runBtn.innerHTML = '▶ Run Tests';
    runStatus.textContent = 'Code executes in an isolated Docker sandbox';
  }
}

function renderTestResults(data) {
  const resultsBox = document.getElementById('test-results');

  const bannerClass = data.all_passed ? 'passed' : 'failed';
  const bannerIcon  = data.all_passed ? '🎉' : '⚠️';

  let html = `
    <div class="results-card">
      <div class="results-banner ${bannerClass}">
        <span>${bannerIcon}</span>
        <span>${escapeHtml(data.summary)}</span>
      </div>
  `;

  // Mistake taxonomy tags
  if (data.mistakes && data.mistakes.length > 0) {
    html += '<div class="mistake-tags-row">';
    data.mistakes.forEach(m => {
      html += `<span class="mistake-badge" title="${escapeHtml(m.evidence)}">🏷️ ${escapeHtml(m.category)} (${escapeHtml(m.confidence)})</span>`;
    });
    html += '</div>';
  }

  // Safe explanation & guidance
  if (data.explanation) {
    html += `
      <div class="explanation-card">
        <div class="explanation-title">🧠 Guidance & Analysis</div>
        <div>${escapeHtml(data.explanation).replace(/\n\n/g, '<br><br>')}</div>
      </div>
    `;
  }

  // Canonical outcomes to user-facing labels mapping (PART 6)
  const OUTCOME_DISPLAY = {
    'passed': { label: 'Right', cls: 'outcome-right', icon: '✓' },
    'wrong output': { label: 'Wrong', cls: 'outcome-wrong', icon: '✗' },
    'runtime error': { label: 'Runtime Error', cls: 'outcome-runtime-error', icon: '⚠️' },
    'timeout': { label: 'Run Forever / Timeout', cls: 'outcome-timeout', icon: '⏱️' },
  };

  html += `
    <div class="results-subhead" style="margin-top: 1.25rem;">Evaluation Outcomes</div>
    <div class="test-results-table-wrap">
      <table class="test-results-table" aria-label="Per-Test Evaluation Outcomes">
        <thead>
          <tr>
            <th scope="col">Test</th>
            <th scope="col">Visibility</th>
            <th scope="col">Result</th>
            <th scope="col">Details</th>
            <th scope="col">Duration</th>
          </tr>
        </thead>
        <tbody>
  `;

  // 1. Visible Tests rows
  (data.visible_tests || []).forEach((vt, i) => {
    const mapping = OUTCOME_DISPLAY[vt.outcome] || { label: vt.outcome, cls: 'outcome-wrong', icon: '•' };
    const dur = vt.execution_time != null ? `${Math.round(vt.execution_time * 1000)}ms` : '—';

    let detailsText = escapeHtml(vt.details || (vt.outcome === 'passed' ? 'Result matched' : ''));
    if (vt.outcome === 'wrong output') {
      detailsText = `Returned result did not match: expected <code>${escapeHtml(vt.expected)}</code>, got <code>${escapeHtml(vt.actual)}</code>`;
    } else if (vt.outcome === 'runtime error') {
      const isLimit = detailsText.includes('limit exceeded');
      const limitCls = isLimit ? 'limit-warning' : '';
      detailsText = `<span class="${limitCls}">${detailsText || escapeHtml(vt.actual || 'Runtime error')}</span>`;
    } else if (vt.outcome === 'timeout') {
      detailsText = `Execution deadline exceeded (stopped after timeout)`;
    }

    html += `
      <tr>
        <td><strong>Test ${vt.test_id || (i + 1)}</strong> <span style="font-size:0.75rem; color:var(--text-dim);">(${escapeHtml(vt.label || 'Visible')})</span></td>
        <td><span class="visibility-badge badge-visible">👁️ Visible</span></td>
        <td><span class="outcome-badge-pill ${mapping.cls}">${mapping.icon} ${mapping.label}</span></td>
        <td class="test-details-text">${detailsText}</td>
        <td><span class="test-duration">${dur}</span></td>
      </tr>
    `;
  });

  // 2. Hidden Tests rows (strict confidentiality: no inputs, expected, actual, or raw tracebacks)
  (data.hidden_tests || []).forEach((ht, i) => {
    const mapping = OUTCOME_DISPLAY[ht.outcome] || { label: ht.outcome, cls: 'outcome-wrong', icon: '•' };
    const dur = ht.execution_time != null ? `${Math.round(ht.execution_time * 1000)}ms` : '—';

    let detailsText = escapeHtml(ht.details || '');
    if (!detailsText) {
      if (ht.outcome === 'passed') detailsText = 'Result matched';
      else if (ht.outcome === 'wrong output') detailsText = 'Returned result did not match';
      else if (ht.outcome === 'timeout') detailsText = 'Execution deadline exceeded';
      else detailsText = 'Runtime error occurred during evaluation';
    }

    const isLimit = detailsText.includes('limit exceeded');
    const limitCls = isLimit ? 'limit-warning' : '';

    html += `
      <tr>
        <td><strong>Test ${(data.visible_tests || []).length + (ht.test_id || (i + 1))}</strong> <span style="font-size:0.75rem; color:var(--text-dim);">(Hidden #${ht.test_id || (i + 1)})</span></td>
        <td><span class="visibility-badge badge-hidden">🔒 Hidden</span></td>
        <td><span class="outcome-badge-pill ${mapping.cls}">${mapping.icon} ${mapping.label}</span></td>
        <td class="test-details-text"><span class="${limitCls}">${detailsText}</span></td>
        <td><span class="test-duration">${dur}</span></td>
      </tr>
    `;
  });

  html += `
        </tbody>
      </table>
    </div>
    <p class="hidden-note" style="margin-top:0.75rem;">🔒 Hidden test inputs, expected values, and raw execution details remain confidential on the server.</p>
  </div>`;

  resultsBox.innerHTML = html;
  animateResultsTable();
}

// ---------------------------------------------------------------------------
// 6. Progressive Hints
// ---------------------------------------------------------------------------

function resetHintsUI() {
  const hintsDisplay = document.getElementById('hints-display');
  const hintBtn      = document.getElementById('request-hint-btn');
  const counterBadge = document.getElementById('hint-counter-badge');

  if (hintsDisplay) {
    hintsDisplay.innerHTML =
      '<p class="hints-placeholder">Click <strong>Request Next Hint</strong> when you\'re stuck for guided questions and conceptual clues.</p>';
  }
  if (hintBtn) {
    hintBtn.disabled = false;
    hintBtn.textContent = '🔍 Request Next Hint';
  }
  if (counterBadge) {
    counterBadge.textContent = '0 / 3 revealed';
  }
}

async function requestNextHint() {
  if (!activeSubmissionId) return;

  const hintBtn      = document.getElementById('request-hint-btn');
  const hintsDisplay = document.getElementById('hints-display');
  const counterBadge = document.getElementById('hint-counter-badge');

  hintBtn.disabled = true;
  hintBtn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Fetching hint…';

  try {
    const response = await fetch('/api/hint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ submission_id: activeSubmissionId }),
    });

    if (!response.ok) {
      let errMsg = `Failed to fetch hint (HTTP ${response.status})`;
      try {
        const errJson = await response.json();
        if (errJson.detail) errMsg = errJson.detail;
      } catch (_) {}
      hintsDisplay.innerHTML += `<div class="hints-exhausted-note" style="color:var(--red)">⚠️ ${escapeHtml(errMsg)}</div>`;
      hintBtn.disabled = false;
      hintBtn.textContent = '🔍 Request Next Hint';
      return;
    }

    const data = await response.json();

    // Clear placeholder on first hint
    const placeholder = hintsDisplay.querySelector('.hints-placeholder');
    if (placeholder) {
      placeholder.remove();
    }

    if (data.status === 'exhausted') {
      const note = document.createElement('div');
      note.className = 'hints-exhausted-note';
      note.textContent = '💡 ' + (data.message || 'All hints have been revealed for this submission.');
      hintsDisplay.appendChild(note);

      hintBtn.disabled = true;
      hintBtn.textContent = 'All hints revealed';
      if (counterBadge) counterBadge.textContent = `${data.total_hints} / ${data.total_hints} revealed`;
      return;
    }

    if (data.hint) {
      const card = document.createElement('div');
      card.className = 'hint-card';
      card.innerHTML = `
        <div class="hint-card-header">
          <span class="hint-num-tag">Hint #${data.hint_number} of ${data.total_hints}</span>
        </div>
        <p class="hint-text">${escapeHtml(data.hint)}</p>
      `;
      hintsDisplay.appendChild(card);

      if (counterBadge) {
        counterBadge.textContent = `${data.hint_number} / ${data.total_hints} revealed`;
      }

      if (!data.has_more) {
        hintBtn.disabled = true;
        hintBtn.textContent = 'All hints revealed';
      } else {
        hintBtn.disabled = false;
        hintBtn.textContent = '🔍 Request Next Hint';
      }
    }

  } catch (err) {
    hintsDisplay.innerHTML += `<div class="hints-exhausted-note" style="color:var(--red)">✗ Network error: ${escapeHtml(err.message)}</div>`;
    hintBtn.disabled = false;
    hintBtn.textContent = '🔍 Request Next Hint';
  }
}

// ---------------------------------------------------------------------------
// 7. Learner Progress & Concept Mastery Dashboard
// ---------------------------------------------------------------------------

async function loadLearnerDashboard(learnerId) {
  const effId = learnerId || (currentUser ? currentUser.user_id : currentLearnerId);
  currentLearnerId = effId;
  const learnerBadge = document.getElementById('current-learner-badge');
  if (learnerBadge) {
    learnerBadge.textContent = currentUser
      ? `Learner: ${currentUser.full_name || currentUser.user_id}`
      : `Learner: ${effId}`;
  }

  try {
    const res = await fetch(`/api/learner/${encodeURIComponent(effId)}`);
    if (!res.ok) return;

    const data = await res.json();

    // 1. Section A: Learning Statistics
    const attEl = document.getElementById('stat-attempted-challenges');
    const passedChEl = document.getElementById('stat-passed-challenges');
    const passRateEl = document.getElementById('stat-pass-rate');
    const totalSubEl = document.getElementById('stat-total-submissions');
    const recCountEl = document.getElementById('stat-recurring-count');
    const recBadgeEl = document.getElementById('recurring-badge');

    const pc = data.progress_counts || {};
    if (attEl) attEl.textContent = pc.total_attempted != null ? pc.total_attempted : (pc.passed_challenges || 0);
    if (passedChEl) passedChEl.textContent = `${pc.passed_challenges || 0} / ${pc.total_challenges || 10}`;
    if (passRateEl) passRateEl.textContent = `${Math.round(pc.pass_rate_percent || 0)}%`;
    if (totalSubEl) totalSubEl.textContent = pc.total_submissions || 0;

    const recurringMistakes = data.recurring_mistakes || [];
    if (recCountEl) recCountEl.textContent = recurringMistakes.length;

    if (recBadgeEl) {
      if (recurringMistakes.length > 0) {
        recBadgeEl.className = 'badge badge--error';
        recBadgeEl.textContent = `${recurringMistakes.length} Detected`;
      } else {
        recBadgeEl.className = 'badge badge--ok';
        recBadgeEl.textContent = 'Clean';
      }
    }

    // Render Recent Learning Activity in Dashboard
    const dashActList = document.getElementById('dash-recent-activity-list');
    if (dashActList) {
      const actItems = data.recent_activity || [];
      if (actItems.length > 0) {
        dashActList.innerHTML = actItems.map(item => {
          const passBadge = item.all_passed
            ? '<span class="badge badge--ok badge--sm">✓ Right</span>'
            : '<span class="badge badge--error badge--sm">✗ Wrong</span>';
          const timeFormatted = item.timestamp
            ? new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' })
            : '';
          return `
            <div class="dash-activity-item">
              <div class="dash-act-left">
                ${passBadge}
                <div>
                  <span class="dash-act-title">${escapeHtml(item.challenge_title)}</span>
                  <div class="dash-act-time">${escapeHtml(item.summary || '')}</div>
                </div>
              </div>
              <div class="dash-act-right">
                <span class="badge badge--sm badge--soon">${item.hints_requested > 0 ? `💡 ${item.hints_requested} hints` : '0 hints'}</span>
                <span class="dash-act-time">${timeFormatted}</span>
                <button class="btn btn--ghost btn--xs" onclick="selectAndOpenChallenge('${item.challenge_id}')">Open in Editor →</button>
              </div>
            </div>
          `;
        }).join('');
      } else {
        dashActList.innerHTML = '<p class="empty-state-text">No challenge submissions recorded yet. Pick a challenge in Workspace to begin!</p>';
      }
    }

    // 2. Section B: Concept Mastery Bars
    const masteryContainer = document.getElementById('mastery-bars-container');
    if (masteryContainer && data.mastery) {
      const concepts = Object.keys(data.mastery).sort();
      let masteryHtml = '';

      concepts.forEach(concept => {
        const val = Math.round(data.mastery[concept] || 0);
        let colorClass = 'empty';
        if (val >= 70) colorClass = 'high';
        else if (val >= 40) colorClass = 'mid';
        else if (val > 0) colorClass = 'low';

        const displayName = concept.charAt(0).toUpperCase() + concept.slice(1);

        masteryHtml += `
          <div class="mastery-item">
            <div class="mastery-item-header">
              <span class="mastery-concept-name">${escapeHtml(displayName)}</span>
              <span class="mastery-pct font-mono">${val}%</span>
            </div>
            <div class="progress-track" role="progressbar" aria-valuenow="${val}" aria-valuemin="0" aria-valuemax="100">
              <div class="progress-fill ${colorClass}" style="width: ${val}%;" data-target-width="${val}%"></div>
            </div>
          </div>
        `;
      });

      masteryContainer.innerHTML = masteryHtml;
      animateMasteryBars();
    }

    // 3. Section C: Recurring Mistakes Analysis
    const distRecCount = document.getElementById('distinct-recurring-count');
    const affChCount   = document.getElementById('affected-challenges-count');
    const mostFreqEl   = document.getElementById('most-frequent-mistake');
    const recContainer = document.getElementById('recurring-mistakes-container');

    const mAnalysis = data.mistake_analysis || {};
    if (distRecCount) distRecCount.textContent = mAnalysis.recurring_categories_count != null ? mAnalysis.recurring_categories_count : recurringMistakes.length;
    if (affChCount)   affChCount.textContent = mAnalysis.affected_challenges_count != null ? mAnalysis.affected_challenges_count : 0;
    if (mostFreqEl)   mostFreqEl.textContent = mAnalysis.most_frequent_category || (recurringMistakes.length > 0 ? recurringMistakes[0] : 'None');

    if (recContainer) {
      const recurringList = (mAnalysis.recurring && mAnalysis.recurring.length > 0)
        ? mAnalysis.recurring
        : null;

      if (recurringList && recurringList.length > 0) {
        let cardsHtml = '';
        recurringList.forEach(item => {
          const prioCls = (item.priority || 'medium').toLowerCase();
          const chLinks = (item.affected_challenges || []).map(ch =>
            `<span class="concept-tag" style="cursor:pointer;" onclick="selectAndOpenChallenge('${ch.id}')" title="Practice challenge in Workspace">${escapeHtml(ch.title)}</span>`
          ).join(' ');

          const conceptsList = (item.concepts || []).map(c =>
            `<span class="concept-tag">${escapeHtml(c)}</span>`
          ).join(' ');

          const evidenceSnippet = (item.evidence && item.evidence.length > 0)
            ? `<div class="mistake-evidence-box"><strong>Observed Evidence:</strong> "${escapeHtml(item.evidence[0])}"</div>`
            : '';

          const practiceBtn = item.practice_challenge
            ? `<button class="btn btn--primary btn--xs" onclick="selectAndOpenChallenge('${item.practice_challenge.id}')">Practise ${escapeHtml(item.practice_challenge.title)} →</button>`
            : '';

          cardsHtml += `
            <div class="mistake-card-item priority-${prioCls}">
              <div class="mistake-card-top">
                <div class="mistake-title-wrap">
                  <span class="mistake-name">${escapeHtml(item.name)}</span>
                  <span class="mistake-priority-badge ${prioCls}">Priority: ${escapeHtml(item.priority)}</span>
                </div>
                <span class="mistake-count-badge">${item.failure_count} failures across ${item.distinct_challenges_count} distinct challenges</span>
              </div>

              <div>
                <span style="font-size:0.8rem; color:var(--text-dim); margin-right:0.35rem;">Affected challenges:</span>
                ${chLinks || '<span style="color:var(--text-dim);">None</span>'}
              </div>

              ${conceptsList ? `<div><span style="font-size:0.8rem; color:var(--text-dim); margin-right:0.35rem;">Associated concepts:</span>${conceptsList}</div>` : ''}

              ${evidenceSnippet}

              <details class="mistake-details-expandable">
                <summary>Taxonomy Identifier &amp; Pattern Details</summary>
                <div class="mistake-details-content">
                  <div>Canonical Identifier: <code class="mistake-id-code">${escapeHtml(item.category_id)}</code></div>
                  <p style="color:var(--text-muted); font-size:0.82rem;">Detected in failed submissions across at least 2 distinct challenge IDs. Passed submissions are excluded from recurrence counts.</p>
                </div>
              </details>

              <div class="mistake-action-bar">
                <span style="font-size:0.8rem; color:var(--text-muted);">Recommended remediation practice:</span>
                ${practiceBtn}
              </div>
            </div>
          `;
        });
        recContainer.innerHTML = cardsHtml;
      } else {
        recContainer.innerHTML = '<p class="empty-state-text">✓ No recurring mistakes detected across multiple challenges. Clean execution record!</p>';
      }
    }

    // 4. Section D: Recommended Practice
    const titleEl   = document.getElementById('rec-challenge-title');
    const reasonEl  = document.getElementById('rec-reason');
    const diffBadge = document.getElementById('rec-difficulty-badge');
    const tagsEl    = document.getElementById('rec-tags-container');
    const openBtn   = document.getElementById('open-recommended-btn');

    const recCh = data.next_recommended_challenge || data.recommended_challenge;
    if (recCh) {
      if (titleEl) titleEl.textContent = recCh.title;
      if (reasonEl) reasonEl.textContent = data.explanation || data.recommendation_reason || '';
      if (diffBadge) {
        diffBadge.className = `difficulty ${recCh.difficulty || 'easy'}`;
        diffBadge.textContent = (recCh.difficulty || 'Easy').toUpperCase();
      }
      if (tagsEl && recCh.tags) {
        tagsEl.innerHTML = recCh.tags.map(t => `<span class="concept-tag">${escapeHtml(t)}</span>`).join('');
      }
      if (openBtn) {
        openBtn.style.display = 'inline-flex';
        openBtn.dataset.id = recCh.id;
        openBtn.textContent = `▶ Practice ${recCh.title} in Workspace`;
        openBtn.onclick = () => selectAndOpenChallenge(recCh.id);
      }
    } else {
      if (titleEl) titleEl.textContent = '🎉 All 10 Challenges Mastered!';
      if (reasonEl) reasonEl.textContent = data.explanation || 'You have successfully conquered every challenge in Debug Dojo. Outstanding debugging!';
      if (openBtn) openBtn.style.display = 'none';
      if (diffBadge) {
        diffBadge.className = 'badge badge--ok';
        diffBadge.textContent = 'Mastered';
      }
    }

  } catch (err) {
    console.error('Failed to load learner dashboard:', err);
  }
}

async function loadHomeSummary(learnerId) {
  const effId = learnerId || (currentUser ? currentUser.user_id : null);
  if (!effId) return;

  const summaryContainer = document.getElementById('home-auth-summary');
  if (!summaryContainer) return;

  try {
    const res = await fetch(`/api/learner/${encodeURIComponent(effId)}`);
    if (!res.ok) return;
    const data = await res.json();

    summaryContainer.classList.remove('hidden');

    const statPassed = document.getElementById('home-stat-passed');
    const statSubs = document.getElementById('home-stat-submissions');
    const statMistakesBadge = document.getElementById('home-stat-mistakes-badge');
    const recName = document.getElementById('home-rec-name');
    const recDiff = document.getElementById('home-rec-diff');
    const recBtn = document.getElementById('home-rec-btn');

    if (statPassed && data.progress_counts) {
      statPassed.textContent = `${data.progress_counts.passed_challenges || 0} / ${data.progress_counts.total_challenges || 10}`;
    }
    if (statSubs && data.progress_counts) {
      statSubs.textContent = data.progress_counts.total_submissions || 0;
    }

    const recurringList = data.recurring_mistakes || [];
    if (statMistakesBadge) {
      if (recurringList.length > 0) {
        statMistakesBadge.className = 'badge badge--error';
        statMistakesBadge.textContent = `${recurringList.length} Detected`;
      } else {
        statMistakesBadge.className = 'badge badge--ok';
        statMistakesBadge.textContent = 'Clean';
      }
    }

    const recCh = data.next_recommended_challenge || data.recommended_challenge;
    if (recCh) {
      if (recName) recName.textContent = recCh.title;
      if (recDiff) {
        recDiff.className = `difficulty ${recCh.difficulty || 'easy'}`;
        recDiff.textContent = (recCh.difficulty || 'Easy').toUpperCase();
      }
      if (recBtn) {
        recBtn.onclick = () => selectAndOpenChallenge(recCh.id);
      }
    }
  } catch (err) {
    console.warn('[Debug Dojo] Error loading home summary:', err);
  }
}

// Backward compatibility alias
const loadHomeDashboard = loadHomeSummary;

function openRecommendedChallenge(challengeId) {
  if (!challengeId) return;
  selectAndOpenChallenge(challengeId);
}

// ---------------------------------------------------------------------------
// 8. Editor Tab-Key Handling & Utility Helpers
// ---------------------------------------------------------------------------

function setupEditorKeyBindings() {
  const editor = document.getElementById('starter-code');
  if (!editor) return;

  // Intercept Tab key to insert 4 spaces without losing focus
  editor.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = editor.selectionStart;
      const end = editor.selectionEnd;
      const value = editor.value;

      editor.value = value.substring(0, start) + '    ' + value.substring(end);
      editor.selectionStart = editor.selectionEnd = start + 4;

      if (activeId) {
        learnerCodeCache[activeId] = editor.value;
      }
    }
  });

  // Track edits in cache
  editor.addEventListener('input', () => {
    if (activeId) {
      learnerCodeCache[activeId] = editor.value;
    }
  });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// 9. Navigation Setup & Keyboard Accessibility
// ---------------------------------------------------------------------------

function setupNavigation() {
  const navTabs = Array.from(document.querySelectorAll('.nav-tabs .nav-tab[data-view]'));
  navTabs.forEach((tab) => {
    // Click opens corresponding view without reloading
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      showView(tab.dataset.view);
    });

    // Keyboard navigation for tablist (Arrow keys, Home, End among visible tabs)
    tab.addEventListener('keydown', (e) => {
      const visibleTabs = navTabs.filter(t => !t.classList.contains('hidden') && t.style.display !== 'none');
      const currentIndex = visibleTabs.indexOf(tab);
      if (currentIndex === -1) return;
      let nextIndex = null;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        nextIndex = (currentIndex + 1) % visibleTabs.length;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        nextIndex = (currentIndex - 1 + visibleTabs.length) % visibleTabs.length;
      } else if (e.key === 'Home') {
        nextIndex = 0;
      } else if (e.key === 'End') {
        nextIndex = visibleTabs.length - 1;
      }

      if (nextIndex !== null) {
        e.preventDefault();
        visibleTabs[nextIndex].focus();
        showView(visibleTabs[nextIndex].dataset.view);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// 10. Examination Mode Launcher & Fallback Handling
// ---------------------------------------------------------------------------

function getSelectedChallenge() {
  if (currentChallenge && currentChallenge.id === activeId) {
    return currentChallenge;
  }
  if (activeId && allChallenges && allChallenges.length > 0) {
    const found = allChallenges.find(c => c.id === activeId);
    if (found) return found;
  }
  if (currentChallenge) {
    return currentChallenge;
  }
  if (allChallenges && allChallenges.length > 0) {
    return allChallenges[0];
  }
  return null;
}

function showExamFallbackBanner(title, examUrl, isBlocked) {
  let banner = document.getElementById('exam-launch-banner');
  if (!banner) {
    const actionRow = document.querySelector('.action-row');
    if (actionRow && actionRow.parentNode) {
      banner = document.createElement('div');
      banner.id = 'exam-launch-banner';
      banner.className = 'exam-launch-banner';
      actionRow.parentNode.insertBefore(banner, actionRow.nextSibling);
    }
  }

  if (!banner) return;

  banner.className = `exam-launch-banner ${isBlocked ? 'warning' : 'success'}`;
  banner.classList.remove('hidden');

  if (isBlocked) {
    banner.innerHTML = `
      <div class="exam-launch-content">
        <span class="exam-launch-icon" aria-hidden="true">⚠️</span>
        <div class="exam-launch-text">
          <strong>Popup blocked by browser:</strong> The official examination window for <em>${escapeHtml(title)}</em> could not open automatically.
          <div class="exam-launch-actions">
            <a href="${escapeHtml(examUrl)}" target="_blank" rel="noopener noreferrer" class="btn btn--primary btn--xs">
              ↗ Open Examination in New Tab
            </a>
            <a href="${escapeHtml(examUrl)}" class="btn btn--secondary btn--xs">
              Open in Current Window
            </a>
          </div>
        </div>
      </div>
      <button type="button" class="btn-icon-only dismiss-btn" aria-label="Dismiss message">✕</button>
    `;
    const dismissBtn = banner.querySelector('.dismiss-btn');
    if (dismissBtn) {
      dismissBtn.addEventListener('click', () => banner.classList.add('hidden'));
    }
  } else {
    banner.innerHTML = `
      <div class="exam-launch-content">
        <span class="exam-launch-icon" aria-hidden="true">🎓</span>
        <div class="exam-launch-text">
          Official examination tab launched for <strong>${escapeHtml(title)}</strong>.
          <span style="margin-left: 8px;">
            <a href="${escapeHtml(examUrl)}" target="_blank" rel="noopener noreferrer" class="exam-reopen-link">
              ↗ Re-open Tab
            </a>
          </span>
        </div>
      </div>
      <button type="button" class="btn-icon-only dismiss-btn" aria-label="Dismiss message">✕</button>
    `;
    const dismissBtn = banner.querySelector('.dismiss-btn');
    if (dismissBtn) {
      dismissBtn.addEventListener('click', () => banner.classList.add('hidden'));
    }
    setTimeout(() => {
      if (banner && !banner.classList.contains('warning')) {
        banner.classList.add('hidden');
      }
    }, 8000);
  }
}

function openExamination(challengeId, sourceBtn, statusEl) {
  // Check authentication
  if (!currentUser) {
    redirectAfterLogin = 'challenges';
    showAuthAlert('login-alert', 'Authentication is required before entering an official timed examination. Please log in or create an account.', 'error');
    showView('login');
    if (statusEl) {
      statusEl.textContent = 'Authentication required to start examination.';
    }
    return;
  }

  // 1. Read the selected challenge's actual ID and difficulty from existing challenge data
  let ch = null;
  if (challengeId && allChallenges && allChallenges.length > 0) {
    ch = allChallenges.find(c => c.id === challengeId);
  }
  if (!ch) {
    ch = getSelectedChallenge();
  }

  const cid = (ch && ch.id) ? ch.id : (challengeId || activeId || 'last_k_total');
  const difficulty = (ch && ch.difficulty) ? ch.difficulty : 'easy';
  const title = (ch && ch.title) ? ch.title : cid;
  const learnerId = currentUser ? currentUser.user_id : (currentLearnerId || 'student1');

  // 2. Build the examination URL with challenge_id, difficulty, and learner_id
  const examUrl = `/exam?challenge_id=${encodeURIComponent(cid)}&difficulty=${encodeURIComponent(difficulty)}&learner_id=${encodeURIComponent(learnerId)}`;

  // UI state: give user immediate feedback that examination is opening
  if (sourceBtn) {
    sourceBtn.disabled = true;
  }
  if (statusEl) {
    statusEl.innerHTML = `🚀 Opening examination for <strong>${escapeHtml(title)}</strong> (${escapeHtml(difficulty.toUpperCase())}) in new tab…`;
  }

  let popupBlocked = false;
  let newTab = null;

  try {
    newTab = window.open(examUrl, '_blank');
    if (!newTab || newTab.closed || typeof newTab.closed === 'undefined') {
      popupBlocked = true;
    }
  } catch (err) {
    popupBlocked = true;
  }

  if (popupBlocked) {
    // 9. If opening a new tab fails, show a useful error and provide an alternative way to open the examination.
    if (statusEl) {
      statusEl.innerHTML = `⚠️ Popup blocked. <a href="${escapeHtml(examUrl)}" target="_blank" rel="noopener noreferrer" style="color:var(--accent);font-weight:600;text-decoration:underline;">Click here to open ${escapeHtml(title)} exam</a> or <a href="${escapeHtml(examUrl)}" style="color:var(--text-muted);text-decoration:underline;">open in this tab</a>.`;
    }
    showExamFallbackBanner(title, examUrl, true);
  } else {
    try {
      if (newTab && newTab.focus) {
        newTab.focus();
      }
    } catch (_) {}

    showExamFallbackBanner(title, examUrl, false);

    if (statusEl) {
      statusEl.innerHTML = `✓ Exam tab launched. <a href="${escapeHtml(examUrl)}" target="_blank" rel="noopener noreferrer" style="color:var(--accent);text-decoration:underline;">Re-open tab</a>`;
      setTimeout(() => {
        if (statusEl && statusEl.innerHTML.includes('Exam tab launched')) {
          statusEl.textContent = 'Code executes in an isolated Docker sandbox';
        }
      }, 5000);
    }
  }

  if (sourceBtn) {
    setTimeout(() => {
      sourceBtn.disabled = false;
    }, 1500);
  }
}

// ---------------------------------------------------------------------------
// 11. Authentication & Account Management
// ---------------------------------------------------------------------------

function getInitials(name) {
  if (!name) return 'DD';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function showAuthAlert(elementId, message, type = 'error') {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = message;
  el.className = `auth-alert auth-alert--${type}`;
  el.classList.remove('hidden');
}

function clearAuthAlert(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = '';
  el.classList.add('hidden');
}

function setFieldError(fieldId, errorId, message) {
  const field = document.getElementById(fieldId);
  const errEl = document.getElementById(errorId);
  if (errEl) {
    errEl.textContent = message;
    errEl.classList.remove('hidden');
  }
  if (field) {
    field.style.borderColor = 'var(--red)';
  }
}

function clearFieldErrors(form) {
  if (!form) return;
  const errs = form.querySelectorAll('.form-field-err');
  errs.forEach(e => {
    e.textContent = '';
    e.classList.add('hidden');
  });
  const inputs = form.querySelectorAll('.form-input');
  inputs.forEach(i => {
    i.style.borderColor = '';
  });
}

function setupPasswordToggles() {
  const toggles = [
    { btnId: 'toggle-signup-pwd', inputId: 'signup-password' },
    { btnId: 'toggle-signup-confirm-pwd', inputId: 'signup-confirm-password' },
    { btnId: 'toggle-login-pwd', inputId: 'login-password' },
    { btnId: 'toggle-cur-pwd', inputId: 'current-pwd' },
    { btnId: 'toggle-new-pwd', inputId: 'new-pwd' },
    { btnId: 'toggle-conf-pwd', inputId: 'confirm-new-pwd' },
  ];

  toggles.forEach(({ btnId, inputId }) => {
    const btn = document.getElementById(btnId);
    const input = document.getElementById(inputId);
    if (btn && input) {
      btn.addEventListener('click', () => {
        const isPwd = input.type === 'password';
        input.type = isPwd ? 'text' : 'password';
        btn.textContent = isPwd ? '🙈' : '👁';
        btn.setAttribute('aria-label', isPwd ? 'Hide password' : 'Show password');
      });
    }
  });
}

async function checkAuthSession() {
  try {
    const res = await fetch('/api/auth/me');
    if (res.ok) {
      currentUser = await res.json();
      currentLearnerId = currentUser.user_id;
      updateAuthUI(true);
    } else {
      currentUser = null;
      updateAuthUI(false);
    }
  } catch (err) {
    console.warn('[Debug Dojo] Error checking auth session:', err);
    currentUser = null;
    updateAuthUI(false);
  }
}

function updateAuthUI(isAuthenticated) {
  const visitorActions = document.getElementById('nav-visitor-actions');
  const userActions = document.getElementById('nav-user-actions');
  const workspaceNavTab = document.getElementById('nav-workspace-btn');
  const dashboardNavTab = document.getElementById('nav-dashboard-btn');
  const accountNavTab = document.getElementById('nav-account-btn');
  const landingNavTab = document.getElementById('nav-landing-btn');
  const homeNavTab = document.getElementById('nav-home-btn');
  const initialsEl = document.getElementById('nav-user-initials');
  const nameEl = document.getElementById('nav-user-name');
  const learnerBadge = document.getElementById('current-learner-badge');

  // Adaptive Homepage Elements
  const heroBadgeVisitor = document.getElementById('hero-badge-visitor');
  const heroBadgeAuth = document.getElementById('hero-badge-auth');
  const heroUserName = document.getElementById('hero-user-name');
  const heroVisitorCtas = document.getElementById('hero-visitor-ctas');
  const heroAuthCtas = document.getElementById('hero-auth-ctas');
  const ctaVisitorBox = document.getElementById('cta-visitor-box');
  const ctaAuthBox = document.getElementById('cta-auth-box');
  const homeAuthSummary = document.getElementById('home-auth-summary');

  if (isAuthenticated && currentUser) {
    if (visitorActions) visitorActions.classList.add('hidden');
    if (userActions) userActions.classList.remove('hidden');
    if (workspaceNavTab) workspaceNavTab.classList.remove('hidden');
    if (dashboardNavTab) dashboardNavTab.classList.remove('hidden');
    if (accountNavTab) accountNavTab.classList.remove('hidden');
    if (landingNavTab) landingNavTab.classList.add('hidden');
    if (homeNavTab) homeNavTab.classList.remove('hidden');

    if (heroBadgeVisitor) heroBadgeVisitor.classList.add('hidden');
    if (heroBadgeAuth) heroBadgeAuth.classList.remove('hidden');
    if (heroUserName) heroUserName.textContent = currentUser.full_name || currentUser.user_id || 'Learner';
    if (heroVisitorCtas) heroVisitorCtas.classList.add('hidden');
    if (heroAuthCtas) heroAuthCtas.classList.remove('hidden');
    if (ctaVisitorBox) ctaVisitorBox.classList.add('hidden');
    if (ctaAuthBox) ctaAuthBox.classList.remove('hidden');

    if (initialsEl) initialsEl.textContent = getInitials(currentUser.full_name);
    if (nameEl) nameEl.textContent = currentUser.full_name || 'My Account';
    if (learnerBadge) learnerBadge.textContent = `Learner: ${currentUser.full_name || currentUser.user_id}`;

    // If currently on home view, load quick learning summary
    const homeView = document.getElementById('view-home');
    if (homeView && !homeView.classList.contains('hidden')) {
      loadHomeSummary(currentUser.user_id);
    }
  } else {
    if (visitorActions) visitorActions.classList.remove('hidden');
    if (userActions) userActions.classList.add('hidden');
    if (workspaceNavTab) workspaceNavTab.classList.add('hidden');
    if (dashboardNavTab) dashboardNavTab.classList.add('hidden');
    if (accountNavTab) accountNavTab.classList.add('hidden');
    if (landingNavTab) landingNavTab.classList.add('hidden');
    if (homeNavTab) homeNavTab.classList.remove('hidden');

    if (heroBadgeVisitor) heroBadgeVisitor.classList.remove('hidden');
    if (heroBadgeAuth) heroBadgeAuth.classList.add('hidden');
    if (heroVisitorCtas) heroVisitorCtas.classList.remove('hidden');
    if (heroAuthCtas) heroAuthCtas.classList.add('hidden');
    if (ctaVisitorBox) ctaVisitorBox.classList.remove('hidden');
    if (ctaAuthBox) ctaAuthBox.classList.add('hidden');
    if (homeAuthSummary) homeAuthSummary.classList.add('hidden');

    if (learnerBadge) learnerBadge.textContent = 'Learner: Guest';
  }
}

// Signup handler
async function handleSignup(e) {
  e.preventDefault();
  const form = document.getElementById('signup-form');
  clearFieldErrors(form);
  clearAuthAlert('signup-alert');

  const nameInput = document.getElementById('signup-name');
  const emailInput = document.getElementById('signup-email');
  const ageInput = document.getElementById('signup-age');
  const pwdInput = document.getElementById('signup-password');
  const confirmInput = document.getElementById('signup-confirm-password');
  const submitBtn = document.getElementById('signup-submit-btn');

  const fullName = nameInput ? nameInput.value.trim() : '';
  const email = emailInput ? emailInput.value.trim() : '';
  const ageVal = ageInput && ageInput.value.trim() ? parseInt(ageInput.value.trim(), 10) : null;
  const password = pwdInput ? pwdInput.value : '';
  const confirmPassword = confirmInput ? confirmInput.value : '';

  let hasError = false;

  if (!fullName) {
    setFieldError('signup-name', 'signup-name-err', 'Full name is required.');
    hasError = true;
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email || !emailRegex.test(email)) {
    setFieldError('signup-email', 'signup-email-err', 'Please enter a valid email address.');
    hasError = true;
  }

  if (ageVal !== null && (isNaN(ageVal) || ageVal < 1 || ageVal > 120)) {
    setFieldError('signup-age', 'signup-age-err', 'Age must be between 1 and 120.');
    hasError = true;
  }

  if (!password || password.length < 8) {
    setFieldError('signup-password', 'signup-password-err', 'Password must be at least 8 characters long.');
    hasError = true;
  }

  if (password !== confirmPassword) {
    setFieldError('signup-confirm-password', 'signup-confirm-err', 'Passwords do not match.');
    hasError = true;
  }

  if (hasError) return;

  // Loading state
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.querySelector('.btn-text')?.classList.add('hidden');
    submitBtn.querySelector('.btn-spinner')?.classList.remove('hidden');
  }

  try {
    const payload = {
      full_name: fullName,
      email: email,
      password: password,
      confirm_password: confirmPassword,
    };
    if (ageVal !== null) {
      payload.age = ageVal;
    }

    const res = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      currentUser = data.user;
      currentLearnerId = currentUser.user_id;
      updateAuthUI(true);
      showAuthAlert('signup-alert', 'Account created successfully! Redirecting…', 'success');
      form.reset();

      setTimeout(() => {
        clearAuthAlert('signup-alert');
        const next = redirectAfterLogin || 'dashboard';
        redirectAfterLogin = null;
        showView(next);
      }, 1000);
    } else {
      showAuthAlert('signup-alert', data.detail || 'Failed to create account. Please try again.', 'error');
    }
  } catch (err) {
    showAuthAlert('signup-alert', 'Network error creating account. Please check backend connection.', 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.querySelector('.btn-text')?.classList.remove('hidden');
      submitBtn.querySelector('.btn-spinner')?.classList.add('hidden');
    }
  }
}

// Login handler
async function handleLogin(e) {
  e.preventDefault();
  const form = document.getElementById('login-form');
  clearFieldErrors(form);
  clearAuthAlert('login-alert');

  const emailInput = document.getElementById('login-email');
  const pwdInput = document.getElementById('login-password');
  const submitBtn = document.getElementById('login-submit-btn');

  const email = emailInput ? emailInput.value.trim() : '';
  const password = pwdInput ? pwdInput.value : '';

  let hasError = false;
  if (!email) {
    setFieldError('login-email', 'login-email-err', 'Email is required.');
    hasError = true;
  }
  if (!password) {
    setFieldError('login-password', 'login-password-err', 'Password is required.');
    hasError = true;
  }
  if (hasError) return;

  // Loading state
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.querySelector('.btn-text')?.classList.add('hidden');
    submitBtn.querySelector('.btn-spinner')?.classList.remove('hidden');
  }

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      currentUser = data.user;
      currentLearnerId = currentUser.user_id;
      updateAuthUI(true);
      form.reset();

      const next = redirectAfterLogin || 'dashboard';
      redirectAfterLogin = null;
      showView(next);
    } else {
      // General invalid-credentials message to avoid revealing account existence
      showAuthAlert('login-alert', data.detail || 'Invalid email or password.', 'error');
    }
  } catch (err) {
    showAuthAlert('login-alert', 'Network error connecting to login service.', 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.querySelector('.btn-text')?.classList.remove('hidden');
      submitBtn.querySelector('.btn-spinner')?.classList.add('hidden');
    }
  }
}

// Logout handler
async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (_) {}

  currentUser = null;
  currentLearnerId = 'student1';
  updateAuthUI(false);
  showView('home');
}

// Account page loader - dedicated strictly to personal profile and account settings
async function loadAccountData() {
  if (!currentUser) return;
  const profileForm = document.getElementById('profile-edit-form');
  clearAuthAlert('profile-feedback');
  clearAuthAlert('pwd-feedback');

  try {
    const res = await fetch('/api/account');
    if (!res.ok) {
      const headerName = document.getElementById('acc-header-name');
      if (headerName) headerName.textContent = currentUser?.full_name || 'My Account';
      const headerEmail = document.getElementById('acc-header-email');
      if (headerEmail) headerEmail.textContent = currentUser?.email || '';
      const avatarLarge = document.getElementById('acc-avatar-large');
      if (avatarLarge) avatarLarge.textContent = getInitials(currentUser?.full_name || '');
      console.warn('[Debug Dojo] /api/account returned', res.status);
      return;
    }
    const data = await res.json();
    const u = data.user;

    // Header & Info
    const avatarLarge = document.getElementById('acc-avatar-large');
    const headerName = document.getElementById('acc-header-name');
    const headerEmail = document.getElementById('acc-header-email');
    const fullNameIn = document.getElementById('acc-fullname');
    const emailIn = document.getElementById('acc-email');
    const ageIn = document.getElementById('acc-age');
    const createdAtEl = document.getElementById('acc-created-at');
    const userIdEl = document.getElementById('acc-user-id');
    const statusBadge = document.getElementById('acc-status-badge');

    if (avatarLarge) avatarLarge.textContent = getInitials(u.full_name);
    if (headerName) headerName.textContent = u.full_name || 'My Account';
    if (headerEmail) headerEmail.textContent = u.email;
    if (fullNameIn) fullNameIn.value = u.full_name || '';
    if (emailIn) emailIn.value = u.email || '';
    if (ageIn) ageIn.value = (u.age !== null && u.age !== undefined) ? u.age : '';
    if (createdAtEl && u.created_at) {
      const dt = new Date(u.created_at);
      createdAtEl.textContent = isNaN(dt.getTime()) ? u.created_at : dt.toLocaleDateString();
    }
    if (userIdEl) userIdEl.textContent = u.user_id;
    if (statusBadge) statusBadge.textContent = u.status === 'active' ? 'Active Learner' : u.status;
  } catch (err) {
    console.warn('[Debug Dojo] Error loading account data:', err);
    const headerName = document.getElementById('acc-header-name');
    if (headerName) headerName.textContent = currentUser?.full_name || 'My Account';
    const headerEmail = document.getElementById('acc-header-email');
    if (headerEmail) headerEmail.textContent = currentUser?.email || '';
    const avatarLarge = document.getElementById('acc-avatar-large');
    if (avatarLarge) avatarLarge.textContent = getInitials(currentUser?.full_name || '');
  }
}

// Profile edit save
async function handleProfileSave(e) {
  e.preventDefault();
  clearAuthAlert('profile-feedback');

  const fullNameIn = document.getElementById('acc-fullname');
  const ageIn = document.getElementById('acc-age');
  const saveBtn = document.getElementById('save-profile-btn');

  const full_name = fullNameIn ? fullNameIn.value.trim() : '';
  const ageVal = ageIn && ageIn.value.trim() ? parseInt(ageIn.value.trim(), 10) : null;

  if (!full_name) {
    showAuthAlert('profile-feedback', 'Full name cannot be empty.', 'error');
    return;
  }

  if (ageVal !== null && (isNaN(ageVal) || ageVal < 1 || ageVal > 120)) {
    showAuthAlert('profile-feedback', 'Age must be between 1 and 120.', 'error');
    return;
  }

  if (saveBtn) saveBtn.disabled = true;

  try {
    const payload = { full_name };
    if (ageVal !== null) payload.age = ageVal;

    const res = await fetch('/api/account', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      currentUser = data.user;
      updateAuthUI(true);
      showAuthAlert('profile-feedback', 'Profile updated successfully!', 'success');
      loadAccountData();
    } else {
      showAuthAlert('profile-feedback', data.detail || 'Failed to update profile.', 'error');
    }
  } catch (err) {
    showAuthAlert('profile-feedback', 'Network error updating profile.', 'error');
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
}

// Change password
async function handleChangePassword(e) {
  e.preventDefault();
  clearAuthAlert('pwd-feedback');

  const curIn = document.getElementById('current-pwd');
  const newIn = document.getElementById('new-pwd');
  const confIn = document.getElementById('confirm-new-pwd');
  const submitBtn = document.getElementById('save-pwd-btn');

  const current_password = curIn ? curIn.value : '';
  const new_password = newIn ? newIn.value : '';
  const confirm_new_password = confIn ? confIn.value : '';

  if (!current_password) {
    showAuthAlert('pwd-feedback', 'Current password is required.', 'error');
    return;
  }
  if (!new_password || new_password.length < 8) {
    showAuthAlert('pwd-feedback', 'New password must be at least 8 characters long.', 'error');
    return;
  }
  if (new_password !== confirm_new_password) {
    showAuthAlert('pwd-feedback', 'New password and confirmation do not match.', 'error');
    return;
  }

  if (submitBtn) submitBtn.disabled = true;

  try {
    const res = await fetch('/api/account/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password, new_password, confirm_new_password }),
    });

    const data = await res.json().catch(() => ({}));

    if (res.ok) {
      showAuthAlert('pwd-feedback', 'Password changed successfully!', 'success');
      curIn.value = '';
      newIn.value = '';
      confIn.value = '';
    } else {
      showAuthAlert('pwd-feedback', data.detail || 'Failed to update password.', 'error');
    }
  } catch (err) {
    showAuthAlert('pwd-feedback', 'Network error updating password.', 'error');
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// 12. Entry point & Event Listeners
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
  // Health check
  checkHealth();
  setInterval(checkHealth, 30_000);

  // Check backend authentication session first
  await checkAuthSession();

  // Load challenges catalogue and learner dashboard
  loadChallengeList();

  const effUser = currentUser ? currentUser.user_id : currentLearnerId;
  loadLearnerDashboard(effUser);
  if (currentUser) {
    loadHomeDashboard(effUser);
  }

  // Setup editor Tab key handler
  setupEditorKeyBindings();

  // Setup navigation click and keyboard accessibility
  setupNavigation();

  // Setup password show/hide toggles
  setupPasswordToggles();

  // Global [data-view] click handler for buttons and links across page
  document.querySelectorAll('[data-view]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      showView(el.dataset.view);
    });
  });

  // Brand button takes user to unified shared home
  const brandBtn = document.getElementById('brand-home-btn');
  if (brandBtn) {
    brandBtn.addEventListener('click', () => {
      showView('home');
    });
  }

  // Initial view routing based on pathname or auth state
  const rawPath = window.location.pathname.replace(/^\//, '');
  if (rawPath === 'home' || rawPath === 'landing' || (!rawPath && currentUser)) {
    showView('home');
  } else if (rawPath && VALID_VIEWS.includes(rawPath)) {
    showView(rawPath);
  } else {
    showView('home');
  }

  // Hero primary CTA: Start Learning
  const heroStartBtn = document.getElementById('hero-start-learning-btn');
  if (heroStartBtn) {
    heroStartBtn.addEventListener('click', () => {
      if (currentUser) {
        showView('challenges');
      } else {
        showView('signup');
      }
    });
  }

  // Auth form submissions
  const signupForm = document.getElementById('signup-form');
  if (signupForm) signupForm.addEventListener('submit', handleSignup);

  const loginForm = document.getElementById('login-form');
  if (loginForm) loginForm.addEventListener('submit', handleLogin);

  // Logout handlers
  ['nav-logout-btn', 'account-top-logout-btn', 'acc-logout-bottom-btn'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.addEventListener('click', handleLogout);
  });

  // Account form submissions
  const profileForm = document.getElementById('profile-edit-form');
  if (profileForm) profileForm.addEventListener('submit', handleProfileSave);

  const cancelProfileBtn = document.getElementById('cancel-profile-btn');
  if (cancelProfileBtn) cancelProfileBtn.addEventListener('click', loadAccountData);

  const changePwdForm = document.getElementById('change-password-form');
  if (changePwdForm) changePwdForm.addEventListener('submit', handleChangePassword);

  // Mobile challenges list toggle
  const mobToggle = document.getElementById('nav-mobile-challenges-btn');
  if (mobToggle) {
    mobToggle.addEventListener('click', () => {
      showView('workspace');
      toggleMobileSidebar();
    });
  }

  // Welcome starter button
  const welcomeStarterBtn = document.getElementById('welcome-starter-btn');
  if (welcomeStarterBtn) {
    welcomeStarterBtn.addEventListener('click', () => {
      loadChallengeDetail('last_k_total', 1);
      showView('workspace');
    });
  }

  // Reset code button
  const resetBtn = document.getElementById('reset-code-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', resetActiveChallengeCode);
  }

  // Run tests button
  const runBtn = document.getElementById('run-btn');
  if (runBtn) {
    runBtn.addEventListener('click', submitCode);
  }

  // Start exam from workspace button
  const startExamWorkspaceBtn = document.getElementById('start-exam-workspace-btn');
  if (startExamWorkspaceBtn) {
    let openingWorkspaceExam = false;
    startExamWorkspaceBtn.addEventListener('click', () => {
      if (openingWorkspaceExam) return;
      openingWorkspaceExam = true;
      const statusEl = document.getElementById('run-status');
      openExamination(activeId, startExamWorkspaceBtn, statusEl);
      setTimeout(() => {
        openingWorkspaceExam = false;
      }, 1500);
    });
  }

  // Progressive hints button
  const hintBtn = document.getElementById('request-hint-btn');
  if (hintBtn) {
    hintBtn.addEventListener('click', requestNextHint);
  }

  // Recommended challenge jump button
  const recBtn = document.getElementById('open-recommended-btn');
  if (recBtn) {
    recBtn.addEventListener('click', () => {
      openRecommendedChallenge(recBtn.dataset.id);
    });
  }

  // Live challenge filter search
  const searchInput = document.getElementById('challenge-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      filterChallenges(e.target.value);
    });
  }

  // Handle URL path on first load (e.g. /login, /signup, /account)
  const initialPath = window.location.pathname.replace(/^\//, '').toLowerCase();
  const urlParams = new URLSearchParams(window.location.search);
  const redirectParam = urlParams.get('redirect');
  if (redirectParam) {
    redirectAfterLogin = redirectParam;
  }
  if (initialPath && VALID_VIEWS.includes(initialPath)) {
    showView(initialPath);
  } else if (window.location.hash) {
    handleHashNavigation();
  }
});


// ── Cross-Tab Exam Navigation & Hash Router ──────────────────────────────
window.addEventListener('hashchange', handleHashNavigation);

function handleHashNavigation() {
  const hash = window.location.hash;
  if (!hash) return;
  const cleanHash = hash.replace(/^#/, '');
  const [viewPart, queryPart] = cleanHash.split('?');
  const viewName = viewPart.toLowerCase();

  if (VALID_VIEWS.includes(viewName)) {
    showView(viewName);
    if (queryPart) {
      const params = new URLSearchParams(queryPart);
      const highlightId = params.get('highlight');
      if (highlightId) {
        setTimeout(() => highlightChallengeCard(highlightId), 350);
      }
    }
  }
}

window.addEventListener('message', (event) => {
  // Validate origin strictly
  if (event.origin !== window.location.origin) return;
  const msg = event.data;
  if (!msg || typeof msg !== 'object') return;
  if (msg.type !== 'debug_dojo_exam_complete') return;

  if (msg.action === 'navigate') {
    const target = String(msg.target || '#challenges');

    // Parse highlight parameter if present
    const qIdx = target.indexOf('?');
    let highlightId = null;
    if (qIdx !== -1) {
      const params = new URLSearchParams(target.substring(qIdx));
      highlightId = params.get('highlight');
    }

    showView('challenges');

    // Highlight the specific challenge if requested
    if (highlightId) {
      setTimeout(() => highlightChallengeCard(highlightId), 300);
    }
  }
});

/**
 * Temporarily highlight a specific challenge card in the catalogue grid.
 * Scrolls it into view and applies a pulsing outline for a few seconds.
 */
function highlightChallengeCard(challengeId) {
  if (!challengeId) return;

  const grid = document.getElementById('challenges-grid');
  if (!grid) return;

  const cleanId = challengeId.replace(/-/g, '_');
  const cards = grid.querySelectorAll('.challenge-card');
  let targetCard = null;

  for (const card of cards) {
    if (card.dataset.id === challengeId || card.dataset.id === cleanId) {
      targetCard = card;
      break;
    }
    const btn = card.querySelector(`[data-id="${challengeId}"], [data-id="${cleanId}"]`);
    if (btn) {
      targetCard = card;
      break;
    }
  }

  if (!targetCard) {
    const sidebarItems = document.querySelectorAll('#challenge-list .challenge-item');
    for (const item of sidebarItems) {
      if (item.dataset.id === challengeId || item.dataset.id === cleanId) {
        item.click();
        item.scrollIntoView({ behavior: 'smooth', block: 'center' });
        item.classList.add('challenge-highlight');
        setTimeout(() => item.classList.remove('challenge-highlight'), 3000);
        return;
      }
    }
    return;
  }

  targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });

  targetCard.style.outline = '3px solid #818cf8';
  targetCard.style.outlineOffset = '4px';
  targetCard.style.borderRadius = '10px';
  targetCard.style.boxShadow = '0 0 24px rgba(129, 140, 248, 0.45)';
  targetCard.style.transition = 'all 0.3s ease';

  setTimeout(() => {
    targetCard.style.outline = '';
    targetCard.style.outlineOffset = '';
    targetCard.style.boxShadow = '';
  }, 3500);
}
