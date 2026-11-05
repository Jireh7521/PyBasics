/* PyBasics frontend -- talks to the FastAPI backend at window.API_BASE.
   No business logic lives here: grading, locking, and content all come from
   the server. This file is purely rendering + wiring. */

const topbar = document.getElementById('topbar');
const progressArea = document.getElementById('progressArea');
const app = document.getElementById('app');
const pageFooter = document.getElementById('pageFooter');

const state = {
  screen: 'loading',
  token: localStorage.getItem('pybasics_token') || null,
  fullName: '', username: '',
  authMode: 'login', authError: '',
  currentDay: null, lessonData: null, lessonAnswers: [],
  attempt: null,           // { id, level, type, total, index, score, question }
  codeAnswered: false,
  examLevelsCache: null,
  cert: null,
};

function escapeHtml(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

async function api(path, opts = {}) {
  const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  if (state.token) headers['Authorization'] = 'Bearer ' + state.token;
  const res = await fetch(window.API_BASE + path, Object.assign({}, opts, { headers }));
  let body = null;
  try { body = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    const msg = (body && (body.detail || (Array.isArray(body) && body[0] && body[0].msg))) || 'Request failed.';
    const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    err.status = res.status;
    throw err;
  }
  return body;
}

function setToken(t) {
  state.token = t;
  if (t) localStorage.setItem('pybasics_token', t); else localStorage.removeItem('pybasics_token');
}

function logout(message) {
  setToken(null);
  state.authError = message || '';
  state.screen = 'auth';
  state.attempt = null;
  render();
}

/* ---------------- boot / routing ---------------- */

async function boot() {
  if (!state.token) { state.screen = 'auth'; return render(); }
  try {
    const me = await api('/auth/me');
    state.fullName = me.full_name; state.username = me.username;
    await routeAfterLogin();
  } catch (e) {
    setToken(null); state.screen = 'auth'; render();
  }
}

async function routeAfterLogin() {
  const course = await api('/course/status');
  if (!course.course_complete) { state.screen = 'course'; return render(); }
  state.screen = 'levels'; render();
}

/* ---------------- render dispatch ---------------- */

function render() {
  document.body.classList.toggle('exam-lock', state.screen === 'quiz' || state.screen === 'codeQuiz');
  progressArea.innerHTML = '';
  pageFooter.style.display = 'block';
  if (state.screen === 'loading') { topbar.innerHTML = ''; app.innerHTML = '<div class="card">Loading&hellip;</div>'; return; }
  if (state.screen === 'auth') return renderAuth();
  if (state.screen === 'course') return renderCourse();
  if (state.screen === 'lesson') return renderLesson();
  if (state.screen === 'lessonResult') return renderLessonResultScreen();
  if (state.screen === 'levels') return renderLevels();
  if (state.screen === 'quiz') return renderQuiz();
  if (state.screen === 'codeQuiz') return renderCodeQuiz();
  if (state.screen === 'levelResult') return renderLevelResult();
  if (state.screen === 'certificate') return renderCertificate();
}

/* ---------------- auth ---------------- */

function renderAuth() {
  topbar.innerHTML = `<div class="topbar"><div><div class="brand">Py<em>Basics</em></div><div class="tagline">30-day class &middot; 5-level exam &middot; certificate</div></div></div>`;
  app.innerHTML = `
    <div class="card">
      <div class="auth-tabs">
        <button id="tabLogin" class="${state.authMode === 'login' ? 'active' : ''}">Log in</button>
        <button id="tabSignup" class="${state.authMode === 'signup' ? 'active' : ''}">Sign up</button>
      </div>
      <div class="auth-error ${state.authError ? 'show' : ''}">${escapeHtml(state.authError)}</div>
      ${state.authMode === 'signup' ? `<div class="field"><label for="fullname">Full name <span style="color:var(--slate-300);">(as it should appear on your certificate)</span></label><input id="fullname" autocomplete="name" maxlength="60"></div>` : ''}
      <div class="field"><label for="username">Username</label><input id="username" autocomplete="username"></div>
      <div class="field"><label for="password">Password</label><input id="password" type="password" autocomplete="${state.authMode === 'signup' ? 'new-password' : 'current-password'}"></div>
      <button class="primary-btn" id="authSubmit">${state.authMode === 'signup' ? 'Create account' : 'Log in'}</button>
    </div>`;
  document.getElementById('tabLogin').onclick = () => { state.authMode = 'login'; state.authError = ''; render(); };
  document.getElementById('tabSignup').onclick = () => { state.authMode = 'signup'; state.authError = ''; render(); };
  document.getElementById('authSubmit').onclick = async () => {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    try {
      let resp;
      if (state.authMode === 'signup') {
        const fullName = document.getElementById('fullname').value.trim();
        resp = await api('/auth/signup', { method: 'POST', body: JSON.stringify({ username, password, full_name: fullName }) });
      } else {
        resp = await api('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
      }
      setToken(resp.access_token); state.fullName = resp.full_name; state.username = resp.username; state.authError = '';
      await routeAfterLogin();
    } catch (e) { state.authError = e.message; render(); }
  };
}

/* ---------------- course ---------------- */

async function renderCourse() {
  topbar.innerHTML = `
    <div class="topbar">
      <div><div class="brand">Py<em>Basics</em></div><div class="tagline">30-Day Python Class &mdash; ${escapeHtml(state.fullName)}</div></div>
      <div class="topbar-right"><button class="linklike" id="logoutBtn">Log out</button></div>
    </div>`;
  document.getElementById('logoutBtn').onclick = () => logout();
  app.innerHTML = `<div class="card">Loading your class&hellip;</div>`;
  let data;
  try { data = await api('/course/status'); } catch (e) { app.innerHTML = `<div class="card">${escapeHtml(e.message)}</div>`; return; }

  const tiles = data.lessons.map(l => {
    let cls = 'day-tile', mark = String(l.day);
    if (l.status === 'done') { cls += ' done'; mark = '\u2713'; }
    else if (l.status === 'locked') { cls += ' locked'; mark = '\ud83d\udd12'; }
    const title = l.status === 'locked' ? `${l.title} \u2014 unlocks ${l.unlocks_on}` : l.title;
    return `<button class="${cls}" data-day="${l.day}" ${l.status === 'locked' ? 'disabled' : ''} title="${escapeHtml(title)}">
      <div class="day-num">${mark}</div><div class="day-title">${escapeHtml(l.title)}</div>
    </button>`;
  }).join('');

  app.innerHTML = `
    <div class="card">
      <p class="topic-tag" style="margin-bottom:6px;">Python Fundamentals &mdash; 30-Day Class</p>
      <p style="color:var(--slate-300); font-size:0.88rem; margin:0 0 20px;">One lesson unlocks per calendar day. Complete all 30 to unlock the exam. ${data.completed_count} of ${data.total} completed.</p>
      <div class="progress-rail" style="margin-bottom:22px;"><div class="progress-fill" style="width:${(data.completed_count / data.total * 100)}%"></div></div>
      <div class="day-grid">${tiles}</div>
    </div>`;
  document.querySelectorAll('.day-tile:not(.locked)').forEach(btn => {
    btn.onclick = async () => {
      const day = parseInt(btn.dataset.day, 10);
      try {
        state.lessonData = await api(`/course/day/${day}`);
        state.currentDay = day;
        state.lessonAnswers = new Array(state.lessonData.quiz.length).fill(null);
        state.screen = 'lesson'; render();
      } catch (e) { alert(e.message); }
    };
  });
}

function renderLesson() {
  const lsn = state.lessonData, day = state.currentDay;
  topbar.innerHTML = `
    <div class="topbar">
      <div><div class="brand">Py<em>Basics</em></div><div class="tagline">Day ${day} of 30</div></div>
      <div class="topbar-right"><button class="linklike" id="courseBackBtn">All lessons</button></div>
    </div>`;
  document.getElementById('courseBackBtn').onclick = () => { state.screen = 'course'; render(); };

  const paras = lsn.read.split('\n\n').map(p => `<p>${escapeHtml(p)}</p>`).join('');
  const yt = 'https://www.youtube.com/results?search_query=' + encodeURIComponent(lsn.query);
  const web = 'https://www.google.com/search?q=' + encodeURIComponent(lsn.query);
  const quizHtml = lsn.quiz.map((q, qi) => `
    <div style="margin-bottom:18px;">
      <p class="question" style="margin-bottom:10px;">${qi + 1}. ${escapeHtml(q.q)}</p>
      <div class="options" data-qi="${qi}">
        ${q.options.map((opt, oi) => `<button class="option" data-oi="${oi}"><span class="key">${String.fromCharCode(65 + oi)}</span><span>${escapeHtml(opt)}</span></button>`).join('')}
      </div>
    </div>`).join('');

  app.innerHTML = `
    <div class="card">
      <div class="topic-tag">Day ${day} &middot; ${escapeHtml(lsn.title)}</div>
      <div class="instructions">${paras}</div>
      <pre class="code-editor" style="margin-bottom:10px;">${escapeHtml(lsn.code)}</pre>
      <pre class="code-editor" style="opacity:0.82; border-left-color:var(--navy-700); margin-bottom:6px;">${escapeHtml(lsn.codeNote)}</pre>
      <div class="resource-links">
        <a href="${yt}" target="_blank" rel="noopener">Watch a video on this &rarr;</a>
        <a href="${web}" target="_blank" rel="noopener">Read more about this &rarr;</a>
      </div>
    </div>
    <div class="card">
      <p class="topic-tag" style="margin-bottom:14px;">${lsn.already_completed ? 'Retake the quiz' : 'Quick check'}</p>
      ${quizHtml}
      <div class="auth-error" id="quizErr"></div>
      <button class="primary-btn" id="checkBtn" disabled>Check answers</button>
    </div>`;

  document.querySelectorAll('.options').forEach(group => {
    const qi = parseInt(group.dataset.qi, 10);
    group.querySelectorAll('.option').forEach(btn => {
      btn.onclick = () => {
        state.lessonAnswers[qi] = parseInt(btn.dataset.oi, 10);
        group.querySelectorAll('.option').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        document.getElementById('checkBtn').disabled = state.lessonAnswers.some(a => a === null);
      };
    });
  });

  document.getElementById('checkBtn').onclick = async () => {
    try {
      const result = await api(`/course/day/${day}/submit`, { method: 'POST', body: JSON.stringify({ answers: state.lessonAnswers }) });
      state.lessonResult = result;
      state.screen = 'lessonResult'; render();
    } catch (e) { document.getElementById('quizErr').textContent = e.message; document.getElementById('quizErr').classList.add('show'); }
  };
}

function renderLessonResultScreen() {
  const r = state.lessonResult, lsn = state.lessonData, day = state.currentDay;
  topbar.innerHTML = `<div><div class="brand">Py<em>Basics</em></div><div class="tagline">Day ${day} &mdash; ${escapeHtml(lsn.title)}</div></div>`;
  const lines = r.results.map((res, i) => `
    <div class="feedback show ${res.correct ? 'good' : 'bad'}">
      <strong>Q${i + 1}: ${res.correct ? 'Correct.' : 'Not quite.'}</strong> ${res.explain}
    </div>`).join('');
  const verdict = r.passed
    ? "Nice work \u2014 this day is marked complete."
    : "You need every question right to mark this day complete. Review the lesson and try again.";
  app.innerHTML = `
    <div class="card results">
      <div class="topic-tag">Day ${day} quiz</div>
      <div class="score-big">${r.score} / ${r.total}</div>
      <div class="score-of">correct</div>
      <p class="verdict">${verdict}</p>
      <div style="text-align:left; margin-bottom:20px;">${lines}</div>
      <div class="result-actions">
        ${!r.passed ? `<button class="primary-btn" id="retryBtn" style="width:auto;">Try again</button>` : ''}
        <button class="ghost-btn" id="backCourseBtn">All lessons</button>
      </div>
    </div>`;
  document.getElementById('backCourseBtn').onclick = () => { state.screen = 'course'; render(); };
  if (!r.passed) document.getElementById('retryBtn').onclick = () => {
    state.lessonAnswers = new Array(lsn.quiz.length).fill(null);
    state.screen = 'lesson'; render();
  };
}

/* ---------------- exam: levels dashboard ---------------- */

async function renderLevels() {
  topbar.innerHTML = `
    <div class="topbar">
      <div><div class="brand">Py<em>Basics</em></div><div class="tagline">Exam &mdash; ${escapeHtml(state.fullName)}</div></div>
      <div class="topbar-right"><button class="linklike" id="classBtn">Class</button><button class="linklike" id="logoutBtn">Log out</button></div>
    </div>`;
  document.getElementById('classBtn').onclick = () => { state.screen = 'course'; render(); };
  document.getElementById('logoutBtn').onclick = () => logout();
  app.innerHTML = `<div class="card">Loading&hellip;</div>`;
  let data;
  try { data = await api('/exam/overview'); } catch (e) { app.innerHTML = `<div class="card">${escapeHtml(e.message)}</div>`; return; }
  state.examLevelsCache = data;

  const rows = data.levels.map(lv => {
    let cls = 'level-card', status = 'Not started';
    if (lv.status === 'locked') cls += ' locked';
    if (lv.status === 'passed') { cls += ' passed'; status = `<span class="level-status done">Passed &middot; ${lv.best_score}/${lv.count}</span>`; }
    else if (lv.best_score !== null && lv.best_score !== undefined) status = `<span class="level-status">Best: ${lv.best_score}/${lv.count}</span>`;
    else if (lv.status === 'locked') status = '<span class="level-status">Locked</span>';
    return `<div class="${cls}" data-level="${lv.level}" ${lv.status === 'locked' ? '' : 'role="button"'}>
      <div><div class="level-title">${lv.name} &mdash; ${lv.difficulty}</div><div class="level-sub">${lv.count} questions &middot; ${lv.type === 'code' ? 'Write the code' : 'Multiple choice'}</div></div>
      <div>${status}</div>
    </div>`;
  }).join('');

  app.innerHTML = `
    <div class="card">
      <p class="topic-tag" style="margin-bottom:14px;">Python Fundamentals Exam</p>
      <div class="level-grid">${rows}</div>
      ${data.certificate_ready ? `<button class="primary-btn" id="certBtn" style="margin-top:18px;">View your certificate</button>` : ''}
    </div>`;

  document.querySelectorAll('.level-card:not(.locked)').forEach(card => {
    card.onclick = async () => {
      const level = parseInt(card.dataset.level, 10);
      try {
        const start = await api(`/exam/level/${level}/start`, { method: 'POST' });
        state.attempt = { id: start.attempt_id, level, type: start.type, total: start.total, index: start.question_index, score: 0, question: start.question };
        state.codeAnswered = false;
        state.screen = start.type === 'code' ? 'codeQuiz' : 'quiz';
        render();
      } catch (e) { alert(e.message); }
    };
  });
  if (data.certificate_ready) document.getElementById('certBtn').onclick = () => { state.screen = 'certificate'; render(); };
}

/* ---------------- exam lockdown: leave = abandon + logout ---------------- */

function examActive() { return state.screen === 'quiz' || state.screen === 'codeQuiz'; }

function triggerExamViolation(reason) {
  if (!examActive() || !state.attempt) return;
  const attemptId = state.attempt.id;
  api(`/exam/attempt/${attemptId}/abandon`, { method: 'POST' }).catch(() => {});
  logout(`Your attempt was ended because you left the page (${reason}). Log back in to retake this level from question 1 \u2014 your other progress is untouched.`);
}

document.addEventListener('visibilitychange', () => { if (document.hidden) triggerExamViolation('tab switched or window minimized'); });
window.addEventListener('blur', () => { setTimeout(() => { if (!document.hasFocus()) triggerExamViolation('left the window'); }, 50); });
document.addEventListener('contextmenu', (e) => { if (examActive()) e.preventDefault(); });
document.addEventListener('copy', (e) => { if (examActive()) e.preventDefault(); });
document.addEventListener('cut', (e) => { if (examActive()) e.preventDefault(); });
document.addEventListener('keydown', (e) => {
  if (!examActive()) return;
  const k = e.key.toLowerCase(); const mod = e.ctrlKey || e.metaKey;
  const blocked = (mod && ['c', 'x', 'u', 's', 'p'].includes(k)) || e.key === 'F12' || (mod && e.shiftKey && ['i', 'j', 'c'].includes(k));
  if (blocked) e.preventDefault();
});

/* ---------------- exam: mcq quiz ---------------- */

function renderQuiz() {
  const a = state.attempt, q = a.question;
  progressArea.innerHTML = `
    <div class="progress-rail"><div class="progress-fill" style="width:${(a.index / a.total * 100)}%"></div></div>
    <div class="progress-label"><span>Question ${a.index + 1} of ${a.total}</span><span>Score: ${a.score}</span></div>`;
  topbar.innerHTML = `<div class="topbar"><div><div class="brand">Py<em>Basics</em></div></div><div class="topbar-right"><span class="badge">Level ${a.level}</span></div></div>`;
  app.innerHTML = `
    <div class="card">
      <div class="topic-tag">${escapeHtml(q.topic)}</div>
      <p class="question">${escapeHtml(q.q)}</p>
      ${q.code ? `<pre class="q-code">${escapeHtml(q.code)}</pre>` : ''}
      <div class="options" id="optionsList">
        ${(q.options || []).map((opt, i) => `<button class="option" data-index="${i}"><span class="key">${['A','B','C','D'][i]}</span><span>${escapeHtml(opt)}</span></button>`).join('')}
      </div>
      <div class="feedback" id="feedback"></div>
      <div class="card-foot">
        <button class="submit-btn" id="submitBtn" disabled>Submit answer</button>
        <button class="next-btn" id="nextBtn">${a.index === a.total - 1 ? 'See level results' : 'Next question'}</button>
      </div>
    </div>`;

  let selected = null;
  document.querySelectorAll('.option').forEach(btn => btn.onclick = () => {
    if (btn.disabled) return;
    selected = parseInt(btn.dataset.index, 10);
    document.querySelectorAll('.option').forEach(b => b.classList.toggle('selected', b === btn));
    document.getElementById('submitBtn').disabled = false;
  });

  document.getElementById('submitBtn').onclick = async () => {
    if (selected === null) return;
    document.getElementById('submitBtn').disabled = true;
    let res;
    try { res = await api(`/exam/attempt/${a.id}/answer/mcq`, { method: 'POST', body: JSON.stringify({ selected }) }); }
    catch (e) { alert(e.message); return; }
    document.querySelectorAll('.option').forEach((b, i) => {
      b.disabled = true;
      if (i === res.correct_option) b.classList.add('correct');
      else if (i === selected && !res.correct) b.classList.add('incorrect');
    });
    const fb = document.getElementById('feedback');
    fb.className = 'feedback show ' + (res.correct ? 'good' : 'bad');
    fb.innerHTML = `<strong>${res.correct ? 'Correct.' : 'Not quite.'}</strong> ${res.explain}`;
    document.getElementById('submitBtn').classList.add('hide');
    document.getElementById('nextBtn').classList.add('show');
    a.score = res.score;
    a._finished = res.finished; a._nextQuestion = res.next_question;
  };

  document.getElementById('nextBtn').onclick = () => {
    if (a._finished) { state.screen = 'levelResult'; render(); return; }
    a.index += 1; a.question = a._nextQuestion;
    render();
  };
}

/* ---------------- exam: code quiz (levels 4/5) ---------------- */

function renderCodeQuiz() {
  const a = state.attempt, q = a.question;
  state.codeAnswered = false;
  progressArea.innerHTML = `
    <div class="progress-rail"><div class="progress-fill" style="width:${(a.index / a.total * 100)}%"></div></div>
    <div class="progress-label"><span>Question ${a.index + 1} of ${a.total}</span><span>Score: ${a.score}</span></div>`;
  topbar.innerHTML = `<div class="topbar"><div><div class="brand">Py<em>Basics</em></div></div><div class="topbar-right"><span class="badge">Level ${a.level}</span></div></div>`;
  app.innerHTML = `
    <div class="card">
      <div class="topic-tag">${escapeHtml(q.topic)} &middot; Write the code</div>
      <div class="instructions">${q.q}</div>
      <textarea id="codeInput" class="code-editor" spellcheck="false" autocapitalize="off" autocomplete="off" rows="${q.starter.split('\n').length + 1}">${escapeHtml(q.starter)}</textarea>
      <div class="feedback" id="feedback"></div>
      <div class="card-foot">
        <button class="submit-btn" id="submitBtn">Run &amp; check</button>
        <button class="next-btn" id="nextBtn">${a.index === a.total - 1 ? 'See level results' : 'Next question'}</button>
      </div>
    </div>`;

  const ta = document.getElementById('codeInput');
  ta.addEventListener('keydown', (e) => { if (e.key === 'Tab') { e.preventDefault(); ta.setRangeText('    ', ta.selectionStart, ta.selectionEnd, 'end'); } });

  document.getElementById('submitBtn').onclick = async () => {
    if (state.codeAnswered) return;
    const btn = document.getElementById('submitBtn'); btn.disabled = true; btn.textContent = 'Running\u2026';
    let res;
    try { res = await api(`/exam/attempt/${a.id}/answer/code`, { method: 'POST', body: JSON.stringify({ code: ta.value }) }); }
    catch (e) { alert(e.message); btn.disabled = false; btn.textContent = 'Run & check'; return; }
    btn.disabled = false; btn.textContent = 'Run & check';
    const fb = document.getElementById('feedback');
    if (!res.correct) {
      const lines = (res.var_results || []).map(r => `<div><code>${escapeHtml(r.name)}</code> ${r.correct ? '\u2713 correct' : '\u2717 not right yet'}</div>`).join('');
      fb.className = 'feedback show bad';
      fb.innerHTML = `<strong>Not correct yet.</strong> ${res.error ? escapeHtml(res.error) : 'Fix your code and press Run &amp; check again \u2014 you can\u2019t move on until every variable is right.'}<div style="margin:8px 0 0;">${lines}</div>`;
      return;
    }
    state.codeAnswered = true;
    ta.disabled = true;
    const lines = (res.var_results || []).map(r => `<div><code>${escapeHtml(r.name)}</code> \u2713</div>`).join('');
    fb.className = 'feedback show good';
    fb.innerHTML = `<strong>Correct.</strong><div style="margin:8px 0;">${lines}</div>${res.explain || ''}`;
    document.getElementById('nextBtn').classList.add('show');
    document.getElementById('submitBtn').classList.add('hide');
    a.score = res.score;
    a._finished = res.finished; a._nextQuestion = res.next_question;
  };

  document.getElementById('nextBtn').onclick = () => {
    if (a._finished) { state.screen = 'levelResult'; render(); return; }
    a.index += 1; a.question = a._nextQuestion;
    render();
  };
}

/* ---------------- exam: level result ---------------- */

async function renderLevelResult() {
  const a = state.attempt;
  topbar.innerHTML = `<div><div class="brand">Py<em>Basics</em></div><div class="tagline">Level ${a.level} results</div></div>`;
  let overview;
  try { overview = await api('/exam/overview'); } catch (e) { overview = state.examLevelsCache; }
  const lv = overview.levels.find(l => l.level === a.level);
  const passed = lv && lv.status === 'passed';
  app.innerHTML = `
    <div class="card results">
      <div class="topic-tag">Level ${a.level}</div>
      <div class="score-big">${a.score} / ${a.total}</div>
      <div class="score-of">correct</div>
      <p class="verdict">${passed ? 'You passed this level.' : 'You need at least 75% to pass. Try again whenever you\u2019re ready.'}</p>
      <div class="result-actions">
        <button class="ghost-btn" id="backLevelsBtn">Back to levels</button>
      </div>
    </div>`;
  document.getElementById('backLevelsBtn').onclick = () => { state.attempt = null; state.screen = 'levels'; render(); };
}

/* ---------------- certificate ---------------- */

async function renderCertificate() {
  topbar.innerHTML = `<div class="topbar"><div><div class="brand">Py<em>Basics</em></div></div><div class="topbar-right"><button class="linklike" id="backLevelsBtn">Back to levels</button></div></div>`;
  document.getElementById('backLevelsBtn').onclick = () => { state.screen = 'levels'; render(); };
  app.innerHTML = `<div class="card">Loading&hellip;</div>`;
  let cert;
  try { cert = await api('/exam/certificate'); } catch (e) { app.innerHTML = `<div class="card">${escapeHtml(e.message)}</div>`; return; }
  state.cert = cert;
  if (!cert.eligible) { app.innerHTML = `<div class="card">Pass all 5 levels to unlock your certificate.</div>`; return; }

  const sig = cert.signature_url;
  app.innerHTML = `
    <div class="cert">
      <div class="cert-kicker">This certifies that</div>
      <div class="cert-name">${escapeHtml(cert.full_name)}</div>
      <div class="cert-title">has completed the PyBasics Fundamentals Program</div>
      <div class="cert-body">Covering a 30-day fundamentals class and a 5-level exam spanning variables, data types, strings, lists, dictionaries, control flow, type conversion and writing real working code, totaling ${cert.total_questions} questions.</div>
      <div class="cert-meta">
        <div class="cert-meta-col"><div class="cert-meta-label">Issued</div><div>${cert.issued_date}</div></div>
        <div class="cert-meta-col cert-sign-col">
          ${sig ? `<img src="${sig}" class="cert-sign-img" alt="Director signature">` : `<div class="cert-sign-placeholder">\u2014</div>`}
          <div class="cert-sign-rule"></div>
          <div class="cert-meta-label">Program Director</div>
        </div>
        <div class="cert-meta-col"><div class="cert-meta-label">Score</div><div>${cert.total_score}/${cert.total_questions}</div></div>
      </div>
      <svg class="cert-stamp" viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg">
        <defs><path id="stampRing" d="M 80,80 m -60,0 a 60,60 0 1,1 120,0 a 60,60 0 1,1 -120,0" /></defs>
        <circle cx="80" cy="80" r="72" fill="none" stroke="var(--gold)" stroke-width="2"/>
        <circle cx="80" cy="80" r="60" fill="none" stroke="var(--gold)" stroke-width="1"/>
        <circle cx="80" cy="80" r="44" fill="none" stroke="var(--gold)" stroke-width="1" opacity="0.6"/>
        <text font-size="9.5" font-weight="700" letter-spacing="2.5" fill="var(--gold-soft)">
          <textPath href="#stampRing" startOffset="1%">PYBASICS &bull; CERTIFIED &bull; PYTHON FUNDAMENTALS &bull;</textPath>
        </text>
        <path d="M 60,82 L 74,94 L 102,64" fill="none" stroke="var(--gold-soft)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <div class="cert-sign-controls">
        <input type="file" id="sigUpload" accept="image/png,image/jpeg,image/svg+xml" style="display:none;">
        <button class="linklike" id="sigUploadBtn">${sig ? 'Replace director signature' : 'Upload director signature'}</button>
      </div>
      <div class="cert-actions">
        <button class="primary-btn" id="printBtn" style="width:auto;">Save as PDF</button>
      </div>
    </div>`;

  document.getElementById('sigUploadBtn').onclick = () => document.getElementById('sigUpload').click();
  document.getElementById('sigUpload').addEventListener('change', async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    if (!/^image\/(png|jpeg|svg\+xml)$/.test(file.type)) { alert('Please choose a PNG, JPG, or SVG image.'); return; }
    if (file.size > 2 * 1024 * 1024) { alert('That image is a bit large \u2014 please use one under 2MB.'); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      try { await api('/exam/certificate/signature', { method: 'POST', body: JSON.stringify({ data_url: reader.result }) }); render(); }
      catch (e2) { alert(e2.message); }
    };
    reader.readAsDataURL(file);
  });

  document.getElementById('printBtn').onclick = () => savePdf(cert);
}

function drawStamp(doc, cx, cy, r) {
  doc.setDrawColor('#c79a3d');
  doc.setLineWidth(1.1); doc.circle(cx, cy, r, 'S');
  doc.setLineWidth(0.7); doc.circle(cx, cy, r - 10, 'S');
  doc.setLineWidth(0.5); doc.circle(cx, cy, r - 18, 'S');
  const text = 'PYBASICS \u2022 CERTIFIED \u2022 PYTHON FUNDAMENTALS \u2022 ';
  const chars = text.split(''); const n = chars.length;
  doc.setFont('helvetica', 'bold'); doc.setFontSize(6.3); doc.setTextColor('#e7c877');
  chars.forEach((ch, i) => {
    const angle = -90 + (360 * i / n); const rad = angle * Math.PI / 180;
    const x = cx + (r - 5) * Math.cos(rad); const y = cy + (r - 5) * Math.sin(rad);
    doc.text(ch, x, y, { angle: -(angle - 90), align: 'center' });
  });
  doc.setDrawColor('#e7c877'); doc.setLineWidth(2);
  doc.line(cx - r * 0.22, cy + r * 0.02, cx - r * 0.05, cy + r * 0.2);
  doc.line(cx - r * 0.05, cy + r * 0.2, cx + r * 0.28, cy - r * 0.22);
}

function rasterizeToPng(dataUrl) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth || img.width; canvas.height = img.naturalHeight || img.height;
      canvas.getContext('2d').drawImage(img, 0, 0);
      try { resolve({ dataUrl: canvas.toDataURL('image/png'), w: canvas.width, h: canvas.height }); } catch (e) { reject(e); }
    };
    img.onerror = reject; img.src = dataUrl;
  });
}

async function savePdf(cert) {
  const btn = document.getElementById('printBtn'); const orig = btn.textContent;
  btn.disabled = true; btn.textContent = 'Preparing\u2026';
  try {
    const { jsPDF } = window.jspdf || {};
    if (!jsPDF) throw new Error('pdf-lib-missing');
    const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'letter' });
    const W = doc.internal.pageSize.getWidth(), H = doc.internal.pageSize.getHeight();
    doc.setFillColor('#0f1a2e'); doc.rect(0, 0, W, H, 'F');
    doc.setDrawColor('#c79a3d'); doc.setLineWidth(1.5); doc.rect(28, 28, W - 56, H - 56);
    doc.setTextColor('#a9b7cf'); doc.setFont('helvetica', 'normal'); doc.setFontSize(12);
    doc.text('This certifies that', W / 2, 130, { align: 'center' });
    doc.setTextColor('#eef1f7'); doc.setFont('times', 'bolditalic'); doc.setFontSize(38);
    doc.text(cert.full_name, W / 2, 180, { align: 'center' });
    doc.setTextColor('#e7c877'); doc.setFont('helvetica', 'bold'); doc.setFontSize(15);
    doc.text('has completed the PyBasics Fundamentals Program', W / 2, 215, { align: 'center' });
    doc.setTextColor('#a9b7cf'); doc.setFont('helvetica', 'normal'); doc.setFontSize(10.5);
    const body = 'A 30-day fundamentals class and a 5-level exam covering variables, data types, strings, lists, dictionaries, control flow, type conversion and writing real working code.';
    doc.text(doc.splitTextToSize(body, W - 200), W / 2, 250, { align: 'center' });
    doc.setFontSize(11); doc.setTextColor('#c79a3d');
    doc.text(`Issued ${cert.issued_date}      \u00b7      Score: ${cert.total_score}/${cert.total_questions}`, W / 2, H - 60, { align: 'center' });

    if (cert.signature_url) {
      try {
        const raster = await rasterizeToPng(cert.signature_url);
        const maxW = 130, maxH = 34;
        const scale = Math.min(maxW / raster.w, maxH / raster.h, 1);
        const dw = raster.w * scale, dh = raster.h * scale;
        doc.addImage(raster.dataUrl, 'PNG', W / 2 - dw / 2, H - 78 - dh - 4, dw, dh);
      } catch (e) { /* ignore */ }
    }
    doc.setDrawColor('#28406b'); doc.setLineWidth(0.75);
    doc.line(W / 2 - 65, H - 78, W / 2 + 65, H - 78);
    doc.setFontSize(8.5); doc.setTextColor('#c79a3d'); doc.setFont('helvetica', 'normal');
    doc.text('Program Director', W / 2, H - 66, { align: 'center' });
    drawStamp(doc, W - 130, H - 150, 58);

    const blob = doc.output('blob');
    const filename = `PyBasics-Certificate-${cert.full_name}.pdf`.replace(/\s+/g, '_');
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  } catch (e) {
    alert('Could not generate the PDF. Please try again.');
  } finally {
    btn.disabled = false; btn.textContent = orig;
  }
}

boot();
