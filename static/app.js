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
let activeSubmissionId = null;
let currentLearnerId = 'student1';
let isSubmitting = false;

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
// 2. Navigation & View Switching
// ---------------------------------------------------------------------------

const VALID_VIEWS = ['landing', 'challenges', 'workspace', 'dashboard'];

function showView(viewName) {
  if (!viewName) return;
  const cleanName = String(viewName).trim().toLowerCase().replace(/^view-/, '');

  // Validate view names before switching
  if (!VALID_VIEWS.includes(cleanName)) {
    console.warn(`[Debug Dojo] Invalid view name requested: "${viewName}". Must be one of: ${VALID_VIEWS.join(', ')}`);
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
  }

  // Update navigation active state and accessible attributes
  const navTabs = document.querySelectorAll('.nav-tabs .nav-tab[data-view]');
  navTabs.forEach(tab => {
    const isTarget = tab.dataset.view === cleanName;
    tab.classList.toggle('active', isTarget);
    tab.setAttribute('aria-selected', isTarget ? 'true' : 'false');
    tab.setAttribute('tabindex', isTarget ? '0' : '-1');
  });
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

    // Footer with "Solve Challenge" button
    const footer = document.createElement('div');
    footer.className = 'challenge-card-footer';

    const solveBtn = document.createElement('button');
    solveBtn.className = 'btn btn--primary btn--sm solve-challenge-btn';
    solveBtn.textContent = 'Solve Challenge';
    solveBtn.dataset.id = ch.id;
    solveBtn.setAttribute('aria-label', `Solve Challenge: ${ch.title}`);

    solveBtn.addEventListener('click', () => {
      loadChallengeDetail(ch.id, index + 1);
      showView('workspace');
    });

    footer.appendChild(solveBtn);
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
        learner_id: currentLearnerId,
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

    // Render results
    renderTestResults(data);

    // Refresh learner dashboard progress immediately
    loadLearnerDashboard();

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

  // Safe explanation
  if (data.explanation) {
    html += `
      <div class="explanation-card">
        <div class="explanation-title">🧠 Guidance & Analysis</div>
        <div>${escapeHtml(data.explanation).replace(/\n\n/g, '<br><br>')}</div>
      </div>
    `;
  }

  // Visible tests breakdown with exact outcome labels
  html += '<div class="results-subhead">Visible Tests</div>';

  data.visible_tests.forEach((vt) => {
    const outcomeSlug = vt.outcome.replace(/\s+/g, '-');
    const badgeClass  = `outcome-badge ${outcomeSlug}`;

    let diffHtml = '';
    if (vt.outcome === 'wrong output') {
      diffHtml = `
        <div class="test-res-diff">
          <div class="diff-row"><span class="label">Expected:</span> <code>${escapeHtml(vt.expected)}</code></div>
          <div class="diff-row"><span class="label">Actual:</span> <code>${escapeHtml(vt.actual)}</code></div>
        </div>`;
    } else if (vt.outcome === 'runtime error') {
      diffHtml = `
        <div class="test-res-diff">
          <div class="diff-row"><span class="label">Exception:</span> <code>${escapeHtml(vt.actual)}</code></div>
        </div>`;
    } else if (vt.outcome === 'timeout') {
      diffHtml = `
        <div class="test-res-diff">
          <div class="diff-row"><span class="label">Timeout:</span> <code>${escapeHtml(vt.actual)}</code></div>
        </div>`;
    }

    html += `
      <div class="test-res-item">
        <div class="test-res-header">
          <span class="test-res-title">Test #${vt.test_id}: ${escapeHtml(vt.label)}</span>
          <span class="${badgeClass}">${escapeHtml(vt.outcome)}</span>
        </div>
        <div><code>${escapeHtml(vt.call)}</code></div>
        ${diffHtml}
      </div>
    `;
  });

  // Hidden tests breakdown (strict confidentiality preserved)
  html += `
      <div class="results-subhead">Hidden Tests</div>
      <div class="hidden-tests-grid">
  `;

  data.hidden_tests.forEach((ht) => {
    const outcomeSlug = ht.outcome.replace(/\s+/g, '-');
    const badgeClass  = `outcome-badge ${outcomeSlug}`;
    html += `
      <div class="hidden-test-pill">
        <span>Hidden #${ht.test_id}</span>
        <span class="${badgeClass}">${escapeHtml(ht.outcome)}</span>
      </div>
    `;
  });

  html += `
      </div>
      <p class="hidden-note">🔒 Hidden test inputs and expected outputs remain confidential on the server.</p>
    </div>
  `;

  resultsBox.innerHTML = html;
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

async function loadLearnerDashboard(learnerId = currentLearnerId) {
  currentLearnerId = learnerId;
  const learnerBadge = document.getElementById('current-learner-badge');
  if (learnerBadge) learnerBadge.textContent = `Learner: ${learnerId}`;

  try {
    const res = await fetch(`/api/learner/${encodeURIComponent(learnerId)}`);
    if (!res.ok) return;

    const data = await res.json();

    // 1. Quick stats
    const totalSubEl = document.getElementById('stat-total-submissions');
    const passedChEl = document.getElementById('stat-passed-challenges');
    const recCountEl = document.getElementById('stat-recurring-count');
    const recBadgeEl = document.getElementById('recurring-badge');

    if (totalSubEl && data.progress_counts) {
      totalSubEl.textContent = data.progress_counts.total_submissions;
    }
    if (passedChEl && data.progress_counts) {
      passedChEl.textContent = `${data.progress_counts.passed_challenges} / ${data.progress_counts.total_challenges}`;
    }

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

    // 2. Recurring mistakes container
    const recContainer = document.getElementById('recurring-mistakes-container');
    if (recContainer) {
      if (recurringMistakes.length > 0) {
        recContainer.innerHTML = recurringMistakes.map(m =>
          `<span class="mistake-badge" title="Failed across ≥ 2 distinct challenges">⚠️ ${escapeHtml(m)} (recurring)</span>`
        ).join('');
      } else {
        recContainer.innerHTML = '<p class="empty-state-text">✓ No recurring mistakes detected across multiple challenges.</p>';
      }
    }

    // 3. Concept Mastery Bars
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

        masteryHtml += `
          <div class="mastery-item">
            <div class="mastery-item-header">
              <span class="mastery-concept-name">${escapeHtml(concept)}</span>
              <span class="mastery-pct">${val}%</span>
            </div>
            <div class="progress-track" role="progressbar" aria-valuenow="${val}" aria-valuemin="0" aria-valuemax="100">
              <div class="progress-fill ${colorClass}" style="width: ${val}%;"></div>
            </div>
          </div>
        `;
      });

      masteryContainer.innerHTML = masteryHtml;
    }

    // 4. Recommendation Card
    const titleEl   = document.getElementById('rec-challenge-title');
    const reasonEl  = document.getElementById('rec-reason');
    const diffBadge = document.getElementById('rec-difficulty-badge');
    const openBtn   = document.getElementById('open-recommended-btn');

    const recCh = data.next_recommended_challenge || data.recommended_challenge;
    if (recCh) {
      if (titleEl) titleEl.textContent = recCh.title;
      if (reasonEl) reasonEl.textContent = data.explanation || data.recommendation_reason || '';
      if (diffBadge) {
        diffBadge.className = `difficulty ${recCh.difficulty}`;
        diffBadge.textContent = recCh.difficulty.charAt(0).toUpperCase() + recCh.difficulty.slice(1);
      }
      if (openBtn) {
        openBtn.style.display = 'inline-flex';
        openBtn.dataset.id = recCh.id;
        openBtn.textContent = `▶ Jump to ${recCh.title}`;
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

function openRecommendedChallenge(challengeId) {
  if (!challengeId) return;
  const button = document.querySelector(`.challenge-item button[data-id="${challengeId}"]`);
  if (button) {
    button.click();
    switchView('workspace');
    button.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else {
    // If not in DOM yet, load directly
    loadChallengeDetail(challengeId);
  }
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
  navTabs.forEach((tab, index) => {
    // Click opens corresponding view without reloading
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      showView(tab.dataset.view);
    });

    // Keyboard navigation for tablist (Arrow keys, Home, End)
    tab.addEventListener('keydown', (e) => {
      let nextIndex = null;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        nextIndex = (index + 1) % navTabs.length;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        nextIndex = (index - 1 + navTabs.length) % navTabs.length;
      } else if (e.key === 'Home') {
        nextIndex = 0;
      } else if (e.key === 'End') {
        nextIndex = navTabs.length - 1;
      }

      if (nextIndex !== null) {
        e.preventDefault();
        navTabs[nextIndex].focus();
        showView(navTabs[nextIndex].dataset.view);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// 10. Entry point & Event Listeners
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  // Health check
  checkHealth();
  setInterval(checkHealth, 30_000);

  // Load challenges catalogue and learner dashboard
  loadChallengeList();
  loadLearnerDashboard();

  // Setup editor Tab key handler
  setupEditorKeyBindings();

  // Setup navigation click and keyboard accessibility
  setupNavigation();

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
});
