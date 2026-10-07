const topbar = document.getElementById('topbar');
const app = document.getElementById('app');
const pageFooter = document.getElementById('pageFooter');

const state = {
  screen: 'loading',
  user: null,          // { username, full_name }
  courseComplete: false,
  authMode: 'login',
  authError: '',
  courseDay: null,
  lessonData: null,
  lessonQIndex: 0,
  lessonAnswered: false,
  examLevel: null,     // {id, name, difficulty, count, type}
  examQuestions: [],   // public questions from /start
  examQIndex: 0,
  examAnswered: false,
  examResults: [],     // [{correct, topic}] for the breakdown
  examMissedThis: false,
  lastLevelResult: null,
};

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function examActive() { return state.screen === 'quiz'; }

async function triggerExamViolation(reason) {
  if (!examActive()) return;
  const levelId = state.examLevel ? state.examLevel.id : null;
  document.body.classList.remove('exam-lock');
  try { await API.post('/api/exam/violation', { levelId, reason }); } catch (e) { /* best effort */ }
  state.screen = 'auth';
  state.authMode = 'login';
  state.authError = `Your attempt was ended because you left the page (${reason}). Log back in to retake this level from question 1 \u2014 your previously passed levels are untouched.`;
  state.user = null;
  render();
}

document.addEventListener('visibilitychange', () => { if (document.hidden) triggerExamViolation('tab switched or window minimized'); });
window.addEventListener('blur', () => { setTimeout(() => { if (!document.hasFocus()) triggerExamViolation('left the window'); }, 50); });
document.addEventListener('contextmenu', (e) => { if (examActive()) e.preventDefault(); });
document.addEventListener('copy', (e) => { if (examActive()) e.preventDefault(); });
document.addEventListener('cut', (e) => { if (examActive()) e.preventDefault(); });
document.addEventListener('dragstart', (e) => { if (examActive()) e.preventDefault(); });
document.addEventListener('keydown', (e) => {
  if (!examActive()) return;
  const k = e.key.toLowerCase();
  const mod = e.ctrlKey || e.metaKey;
  const blocked = (mod && ['c', 'x', 'u', 's', 'p'].includes(k)) || e.key === 'F12' || (mod && e.shiftKey && ['i', 'j', 'c'].includes(k));
  if (blocked) e.preventDefault();
});

/* ---------------------------------------------------------------- boot */

async function boot() {
  try {
    const me = await API.get('/api/auth/me');
    state.user = { username: me.username, full_name: me.full_name };
    state.courseComplete = me.course_complete;
    state.screen = state.courseComplete ? 'levels' : 'course';
  } catch (e) {
    state.screen = 'auth';
  }
  render();
}

function render() {
  document.body.classList.toggle('exam-lock', state.screen === 'quiz');
  if (state.screen === 'auth') renderAuth();
  else if (state.screen === 'course') renderCourse();
  else if (state.screen === 'lesson') renderLesson();
  else if (state.screen === 'lessonQuiz') renderLessonQuiz();
  else if (state.screen === 'lessonResult') renderLessonResult();
  else if (state.screen === 'levels') renderLevels();
  else if (state.screen === 'quiz') renderQuiz();
  else if (state.screen === 'levelResult') renderLevelResult();
  else if (state.screen === 'certificate') renderCertificate();
}

function logoutUI() {
  return `<button class="linklike" id="logoutBtn">Log out</button>`;
}
function wireLogout() {
  const btn = document.getElementById('logoutBtn');
  if (btn) btn.onclick = async () => {
    try { await API.post('/api/auth/logout'); } catch (e) {}
    state.user = null; state.screen = 'auth'; state.authMode = 'login'; state.authError = '';
    render();
  };
}

/* ---------------------------------------------------------------- auth */

function renderAuth() {
  pageFooter.style.display = 'block';
  topbar.innerHTML = `<div><div class="brand">Py<em>Basics</em></div><div class="tagline">Python Fundamentals Program</div></div>`;
  app.innerHTML = `
    <div class="card">
      <div class="auth-tabs">
        <button class="auth-tab ${state.authMode === 'login' ? 'active' : ''}" id="tabLogin">Log in</button>
        <button class="auth-tab ${state.authMode === 'signup' ? 'active' : ''}" id="tabSignup">Sign up</button>
      </div>
      <div class="auth-error ${state.authError ? 'show' : ''}">${escapeHtml(state.authError)}</div>
      ${state.authMode === 'signup' ? `<div class="field"><label for="fullname">Full name <span style="color:var(--slate-300);">(as it should appear on your certificate)</span></label><input id="fullname" autocomplete="name" maxlength="60"></div>` : ''}
      <div class="field"><label for="username">Username</label><input id="username" autocomplete="username"></div>
      <div class="field"><label for="password">Password</label><input id="password" type="password" autocomplete="${state.authMode === 'login' ? 'current-password' : 'new-password'}"></div>
      <button class="primary-btn" id="authSubmit">${state.authMode === 'login' ? 'Log in' : 'Create account'}</button>
      <p class="auth-note">Passwords are hashed and stored server-side. Signing up starts your 30-day course clock \u2014 one lesson unlocks per calendar day, and the exam opens once all 30 are complete.</p>
    </div>`;
  document.getElementById('tabLogin').onclick = () => { state.authMode = 'login'; state.authError = ''; render(); };
  document.getElementById('tabSignup').onclick = () => { state.authMode = 'signup'; state.authError = ''; render(); };
  document.getElementById('authSubmit').onclick = async () => {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const full_name = state.authMode === 'signup' ? document.getElementById('fullname').value.trim() : undefined;
    try {
      const data = state.authMode === 'signup'
        ? await API.post('/api/auth/signup', { username, password, full_name })
        : await API.post('/api/auth/login', { username, password });
      state.user = { username: data.username, full_name: data.full_name };
      state.courseComplete = data.course_complete;
      state.authError = '';
      state.screen = state.courseComplete ? 'levels' : 'course';
      render();
    } catch (e) {
      state.authError = e.message;
      render();
    }
  };
}

/* ---------------------------------------------------------------- course */

async function renderCourse() {
  pageFooter.style.display = 'block';
  topbar.innerHTML = `
    <div class="topbar">
      <div><div class="brand">Py<em>Basics</em></div><div class="tagline">30-Day Python Fundamentals \u00b7 ${escapeHtml(state.user.full_name)}</div></div>
      <div class="topbar-right">${logoutUI()}</div>
    </div>`;
  wireLogout();
  app.innerHTML = `<div class="card"><p>Loading your course\u2026</p></div>`;
  let lessons;
  try { lessons = await API.get('/api/course'); }
  catch (e) { app.innerHTML = `<div class="card"><p class="auth-error show">${escapeHtml(e.message)}</p></div>`; return; }

  const done = lessons.filter(l => l.completed).length;
  const cards = lessons.map(l => {
    const mark = l.completed ? '\u2713' : l.unlocked ? l.day : '\ud83d\udd12';
    const status = l.completed ? '<span class="done">Completed</span>' : l.unlocked ? 'Ready' : `Unlocks day ${l.day}`;
    return `<button class="level-card ${l.unlocked ? '' : 'locked'}" data-day="${l.day}" ${l.unlocked ? '' : 'disabled'}>
      <div class="level-num">${mark}</div>
      <div class="level-info"><div class="level-title">Day ${l.day} \u2014 ${escapeHtml(l.title)}</div><div class="level-sub">Reading \u00b7 code example \u00b7 practice quiz</div></div>
      <div class="level-status">${status}</div>
    </button>`;
  }).join('');
  app.innerHTML = `
    <div class="card">
      <p class="topic-tag" style="margin-bottom:6px;">Your 30-day course</p>
      <p style="color:var(--slate-300); font-size:0.88rem; margin:0 0 20px;">${done} of ${lessons.length} lessons completed. One new lesson unlocks each calendar day \u2014 the exam opens once all 30 are done.</p>
      <div class="progress-rail" style="margin-bottom:22px;"><div class="progress-fill" style="width:${(done / lessons.length * 100)}%"></div></div>
      <div class="level-grid">${cards}</div>
    </div>`;
  document.querySelectorAll('.level-card:not(.locked)').forEach(btn => {
    btn.onclick = () => { state.courseDay = parseInt(btn.dataset.day, 10); state.screen = 'lesson'; render(); };
  });
}

async function renderLesson() {
  pageFooter.style.display = 'block';
  topbar.innerHTML = `<div><div class="brand">Py<em>Basics</em></div><div class="tagline">Day ${state.courseDay} of 30</div></div>`;
  app.innerHTML = `<div class="card"><p>Loading\u2026</p></div>`;
  let lesson;
  try { lesson = await API.get(`/api/course/${state.courseDay}`); }
  catch (e) { app.innerHTML = `<div class="card"><p class="auth-error show">${escapeHtml(e.message)}</p><button class="ghost-btn" id="backCourseBtn">Back to course</button></div>`;
    document.getElementById('backCourseBtn').onclick = () => { state.screen = 'course'; render(); }; return; }
  state.lessonData = lesson;
  const paragraphs = lesson.read.split('\n\n').map(p => `<p>${escapeHtml(p)}</p>`).join('');
  const resourceUrl = 'https://www.youtube.com/results?search_query=' + encodeURIComponent(lesson.query);
  app.innerHTML = `
    <div class="card">
      <div class="topic-tag">Day ${lesson.day} \u00b7 ${escapeHtml(lesson.title)}</div>
      <div class="instructions">${paragraphs}</div>
      <pre class="code-editor" style="white-space:pre-wrap;">${escapeHtml(lesson.code)}</pre>
      <p style="color:var(--slate-300); font-size:0.8rem; margin:10px 0 0;">${escapeHtml(lesson.codeNote)}</p>
      <p style="margin:16px 0 0;"><a href="${resourceUrl}" target="_blank" rel="noopener noreferrer" class="linklike">\u25b6 Watch a video on this topic</a></p>
      <div class="cert-actions">
        ${lesson.completed ? '<span class="done" style="align-self:center;">\u2713 Completed</span>' : `<button class="primary-btn" id="startQuizBtn" style="width:auto;">Take the practice quiz</button>`}
        <button class="ghost-btn" id="backCourseBtn">Back to course</button>
      </div>
    </div>`;
  document.getElementById('backCourseBtn').onclick = () => { state.screen = 'course'; render(); };
  if (!lesson.completed) document.getElementById('startQuizBtn').onclick = () => {
    state.lessonQIndex = 0; state.lessonAnswered = false; state.screen = 'lessonQuiz'; render();
  };
}

function renderLessonQuiz() {
  pageFooter.style.display = 'block';
  const lesson = state.lessonData;
  const item = lesson.quiz[state.lessonQIndex];
  const isLast = state.lessonQIndex === lesson.quiz.length - 1;
  state.lessonAnswered = false;
  topbar.innerHTML = `<div><div class="brand">Py<em>Basics</em></div><div class="tagline">Day ${lesson.day} practice \u00b7 question ${state.lessonQIndex + 1} of ${lesson.quiz.length}</div></div>`;
  const letters = ['A', 'B', 'C', 'D'];
  const opts = item.options.map((o, i) => `<button class="option" data-i="${i}"><span class="key">${letters[i]}</span><span>${escapeHtml(o)}</span></button>`).join('');
  app.innerHTML = `
    <div class="card">
      <div class="progress-rail" style="margin-bottom:18px;"><div class="progress-fill" style="width:${(state.lessonQIndex / lesson.quiz.length * 100)}%"></div></div>
      <p class="question">${escapeHtml(item.q)}</p>
      <div class="options">${opts}</div>
      <div class="feedback" id="feedback"></div>
      <div class="card-foot">
        <button class="next-btn" id="nextBtn">${isLast ? 'Finish lesson' : 'Next question'}</button>
      </div>
    </div>`;
  document.querySelectorAll('.option').forEach(btn => {
    btn.onclick = async () => {
      if (state.lessonAnswered) return;
      const i = parseInt(btn.dataset.i, 10);
      let res;
      try { res = await API.post(`/api/course/${lesson.day}/answer`, { qIndex: state.lessonQIndex, selected: i }); }
      catch (e) { return; }
      const feedback = document.getElementById('feedback');
      if (res.correct) {
        state.lessonAnswered = true;
        document.querySelectorAll('.option').forEach(b => b.disabled = true);
        btn.classList.add('correct');
        feedback.className = 'feedback show good';
        feedback.innerHTML = `<strong>Correct.</strong> ${escapeHtml(res.explain)}`;
        document.getElementById('nextBtn').classList.add('show');
      } else {
        btn.classList.add('incorrect');
        feedback.className = 'feedback show bad';
        feedback.innerHTML = `<strong>Not quite \u2014 try another option.</strong>`;
      }
    };
  });
  document.getElementById('nextBtn').onclick = async () => {
    if (!state.lessonAnswered) return;
    if (isLast) {
      try { await API.post(`/api/course/${lesson.day}/complete`); } catch (e) {}
      state.screen = 'lessonResult'; render();
    } else {
      state.lessonQIndex += 1; render();
    }
  };
}

async function renderLessonResult() {
  pageFooter.style.display = 'block';
  const lesson = state.lessonData;
  topbar.innerHTML = `<div><div class="brand">Py<em>Basics</em></div><div class="tagline">Day ${lesson.day} complete</div></div>`;
  app.innerHTML = `<div class="card"><p>One moment\u2026</p></div>`;
  let lessons, me;
  try { [lessons, me] = await Promise.all([API.get('/api/course'), API.get('/api/auth/me')]); }
  catch (e) { lessons = []; me = { course_complete: false }; }
  state.courseComplete = me.course_complete;
  const next = lessons.find(l => l.day === lesson.day + 1);
  const verdict = state.courseComplete
    ? "You've completed all 30 days. The exam is now unlocked."
    : next && next.unlocked
      ? `Day ${lesson.day + 1} is already unlocked \u2014 keep going.`
      : `Day ${lesson.day + 1} unlocks tomorrow. See you then.`;
  app.innerHTML = `
    <div class="card results">
      <div class="topic-tag">Day ${lesson.day} \u00b7 ${escapeHtml(lesson.title)}</div>
      <div class="score-big">\u2713</div>
      <div class="score-of">lesson complete</div>
      <p class="verdict">${verdict}</p>
      <div class="result-actions">
        <button class="primary-btn" id="backCourseBtn" style="width:auto;">${state.courseComplete ? 'Go to the exam' : 'Back to course'}</button>
      </div>
    </div>`;
  document.getElementById('backCourseBtn').onclick = () => { state.screen = state.courseComplete ? 'levels' : 'course'; render(); };
}

/* ---------------------------------------------------------------- exam */

async function renderLevels() {
  pageFooter.style.display = 'block';
  topbar.innerHTML = `
    <div class="topbar">
      <div><div class="brand">Py<em>Basics</em></div><div class="tagline">Exam \u00b7 ${escapeHtml(state.user.full_name)}</div></div>
      <div class="topbar-right">${logoutUI()}</div>
    </div>`;
  wireLogout();
  app.innerHTML = `<div class="card"><p>Loading levels\u2026</p></div>`;
  let levels;
  try { levels = await API.get('/api/exam/levels'); }
  catch (e) { app.innerHTML = `<div class="card"><p class="auth-error show">${escapeHtml(e.message)}</p></div>`; return; }

  const allPassed = levels.every(l => l.passed);
  const cards = levels.map(l => {
    const mark = l.passed ? '\u2713' : l.unlocked ? l.id : '\ud83d\udd12';
    const status = l.passed ? `<span class="done">Passed \u00b7 ${l.best}/${l.total}</span>`
      : l.best != null ? `Best: ${l.best}/${l.total}` : l.unlocked ? 'Not started' : 'Locked';
    return `<button class="level-card ${l.unlocked ? '' : 'locked'}" data-id="${l.id}" ${l.unlocked ? '' : 'disabled'}>
      <div class="level-num">${mark}</div>
      <div class="level-info"><div class="level-title">${l.name} \u2014 ${l.difficulty}</div><div class="level-sub">${l.count} questions \u00b7 ${l.type === 'code' ? 'Write the code' : 'Multiple choice'}</div></div>
      <div class="level-status">${status}</div>
    </button>`;
  }).join('');
  app.innerHTML = `
    <div class="card">
      <p class="topic-tag" style="margin-bottom:16px;">Choose a level</p>
      <div class="level-grid">${cards}</div>
      ${allPassed ? `<div class="cert-actions"><button class="primary-btn" id="certBtn" style="width:auto;">View certificate</button></div>` : ''}
    </div>`;
  document.querySelectorAll('.level-card:not(.locked)').forEach(btn => {
    btn.onclick = () => startLevel(parseInt(btn.dataset.id, 10), levels.find(l => l.id === parseInt(btn.dataset.id, 10)));
  });
  if (allPassed) document.getElementById('certBtn').onclick = () => { state.screen = 'certificate'; render(); };
}

async function startLevel(id, meta) {
  try {
    const data = await API.post(`/api/exam/level/${id}/start`);
    state.examLevel = { id, name: meta.name, difficulty: meta.difficulty, count: data.count, type: data.type };
    state.examQuestions = data.questions;
    state.examQIndex = 0;
    state.examResults = [];
    state.screen = 'quiz';
    render();
  } catch (e) {
    alert(e.message);
  }
}

function renderQuiz() {
  const item = state.examQuestions[state.examQIndex];
  if (state.examLevel.type === 'code') renderCodeQuiz(item);
  else renderMcqQuiz(item);
}

function renderMcqQuiz(item) {
  pageFooter.style.display = 'block';
  state.examAnswered = false;
  const lvl = state.examLevel;
  topbar.innerHTML = `<div><div class="brand">Py<em>Basics</em></div><div class="tagline">${lvl.name} \u00b7 question ${state.examQIndex + 1} of ${lvl.count}</div></div>`;
  const letters = ['A', 'B', 'C', 'D'];
  const codeBlock = item.code ? `<pre class="snippet">${escapeHtml(item.code)}</pre>` : '';
  const opts = item.options.map((o, i) => `<button class="option" data-i="${i}"><span class="key">${letters[i]}</span><span>${escapeHtml(o)}</span></button>`).join('');
  app.innerHTML = `
    <div class="card">
      <div class="progress-rail" style="margin-bottom:18px;"><div class="progress-fill" style="width:${(state.examQIndex / lvl.count * 100)}%"></div></div>
      <div class="topic-tag">${escapeHtml(item.topic)}</div>
      <p class="question">${escapeHtml(item.q)}</p>
      ${codeBlock}
      <div class="options">${opts}</div>
      <div class="feedback" id="feedback"></div>
      <div class="card-foot">
        <button class="next-btn" id="nextBtn">${state.examQIndex === lvl.count - 1 ? 'See level results' : 'Next question'}</button>
      </div>
    </div>`;
  document.querySelectorAll('.option').forEach(btn => {
    btn.onclick = async () => {
      if (state.examAnswered) return;
      const i = parseInt(btn.dataset.i, 10);
      let res;
      try { res = await API.post(`/api/exam/level/${lvl.id}/mcq/${state.examQIndex}/answer`, { selected: i }); }
      catch (e) { alert(e.message); return; }
      state.examAnswered = true;
      state.examResults.push({ correct: res.correct, topic: item.topic });
      document.querySelectorAll('.option').forEach((b, bi) => {
        b.disabled = true;
        if (bi === res.correctIndex) b.classList.add('correct');
        else if (bi === i) b.classList.add('incorrect');
      });
      const feedback = document.getElementById('feedback');
      feedback.className = 'feedback show ' + (res.correct ? 'good' : 'bad');
      feedback.innerHTML = `<strong>${res.correct ? 'Correct.' : 'Not quite.'}</strong> ${res.explain}`;
      document.getElementById('nextBtn').classList.add('show');
    };
  });
  document.getElementById('nextBtn').onclick = () => {
    if (!state.examAnswered) return;
    state.examQIndex += 1;
    if (state.examQIndex < state.examQuestions.length) render(); else finishLevel();
  };
}

function renderCodeQuiz(item) {
  pageFooter.style.display = 'block';
  state.examAnswered = false;
  state.examMissedThis = false;
  const lvl = state.examLevel;
  topbar.innerHTML = `<div><div class="brand">Py<em>Basics</em></div><div class="tagline">${lvl.name} \u00b7 question ${state.examQIndex + 1} of ${lvl.count}</div></div>`;
  app.innerHTML = `
    <div class="card">
      <div class="progress-rail" style="margin-bottom:18px;"><div class="progress-fill" style="width:${(state.examQIndex / lvl.count * 100)}%"></div></div>
      <div class="topic-tag">${escapeHtml(item.topic)} \u00b7 Write the code</div>
      <div class="instructions">${item.q}</div>
      <textarea id="codeInput" class="code-editor" spellcheck="false" autocapitalize="off" autocomplete="off" rows="${item.starter.split('\n').length + 1}">${escapeHtml(item.starter)}</textarea>
      <div class="feedback" id="feedback"></div>
      <div class="card-foot">
        <button class="submit-btn" id="submitBtn">Run &amp; check</button>
        <button class="next-btn" id="nextBtn">${state.examQIndex === lvl.count - 1 ? 'See level results' : 'Next question'}</button>
      </div>
    </div>`;
  const ta = document.getElementById('codeInput');
  ta.addEventListener('keydown', (e) => { if (e.key === 'Tab') { e.preventDefault(); ta.setRangeText('    ', ta.selectionStart, ta.selectionEnd, 'end'); } });
  document.getElementById('submitBtn').onclick = () => handleCodeAnswer(item, ta.value);
  document.getElementById('nextBtn').onclick = () => {
    if (!state.examAnswered) return;
    state.examQIndex += 1;
    if (state.examQIndex < state.examQuestions.length) render(); else finishLevel();
  };
}

async function handleCodeAnswer(item, code) {
  if (state.examAnswered) return;
  const lvl = state.examLevel;
  let res;
  try { res = await API.post(`/api/exam/level/${lvl.id}/code/${state.examQIndex}/check`, { code }); }
  catch (e) { alert(e.message); return; }
  const feedback = document.getElementById('feedback');
  if (!res.correct) {
    state.examMissedThis = true;
    const lines = res.error ? '' : res.rows.map(r => `<div><code>${escapeHtml(r.name)}</code> ${r.ok ? '\u2713 correct' : '\u2717 is ' + escapeHtml(r.got) + ' \u2014 not right yet'}</div>`).join('');
    feedback.className = 'feedback show bad';
    feedback.innerHTML = `<strong>Not correct yet.</strong> ${res.error ? escapeHtml(res.error) : 'Fix your code and press Run &amp; check again \u2014 you can\u2019t move on until every variable is right.'}<div style="margin:8px 0 0;">${lines}</div>`;
    return;
  }
  state.examAnswered = true;
  const first = !state.examMissedThis;
  state.examResults.push({ correct: first, topic: item.topic });
  document.getElementById('codeInput').disabled = true;
  const lines = res.rows.map(r => `<div><code>${escapeHtml(r.name)}</code> \u2713 <code>${escapeHtml(r.want)}</code></div>`).join('');
  feedback.className = 'feedback show good';
  feedback.innerHTML = `<strong>Correct${first ? '' : ' (after retrying \u2014 no point for this one)'}.</strong><div style="margin:8px 0;">${lines}</div>${res.explain}`;
  document.getElementById('nextBtn').classList.add('show');
  document.getElementById('submitBtn').classList.add('hide');
}

async function finishLevel() {
  document.body.classList.remove('exam-lock');
  const lvl = state.examLevel;
  let res;
  try { res = await API.post(`/api/exam/level/${lvl.id}/finish`); }
  catch (e) { alert(e.message); state.screen = 'levels'; render(); return; }
  state.lastLevelResult = res;
  state.screen = 'levelResult';
  render();
}

function renderLevelResult() {
  pageFooter.style.display = 'block';
  const lvl = state.examLevel;
  const { score, total, passed } = state.lastLevelResult;
  const isLast = lvl.id === 5;
  topbar.innerHTML = `<div><div class="brand">Py<em>Basics</em></div><div class="tagline">${lvl.name} \u2014 ${lvl.difficulty} results</div></div>`;
  const verdict = passed
    ? (isLast ? "You've completed every level at 75% or higher. Your certificate is ready." : `You've unlocked Level ${lvl.id + 1}.`)
    : `You need at least 75% (${Math.ceil(total * 0.75)}/${total}) to pass. Your other passed levels are unaffected \u2014 just retry this one.`;
  app.innerHTML = `
    <div class="card results">
      <div class="topic-tag">${lvl.name} \u00b7 ${lvl.difficulty}</div>
      <div class="score-big">${score} / ${total}</div>
      <div class="score-of">correct</div>
      <p class="verdict">${verdict}</p>
      <div class="result-actions">
        ${passed && isLast ? `<button class="primary-btn" id="certBtn" style="width:auto;">View certificate</button>` : ''}
        ${passed && !isLast ? `<button class="primary-btn" id="nextLevelBtn" style="width:auto;">Continue to Level ${lvl.id + 1}</button>` : ''}
        ${!passed ? `<button class="primary-btn" id="retryBtn" style="width:auto;">Try ${lvl.name} again</button>` : ''}
        <button class="ghost-btn" id="backBtn">Dashboard</button>
      </div>
    </div>`;
  document.getElementById('backBtn').onclick = () => { state.screen = 'levels'; render(); };
  if (passed && isLast) document.getElementById('certBtn').onclick = () => { state.screen = 'certificate'; render(); };
  if (passed && !isLast) document.getElementById('nextLevelBtn').onclick = async () => {
    try {
      const levels = await API.get('/api/exam/levels');
      const next = levels.find(l => l.id === lvl.id + 1);
      startLevel(next.id, next);
    } catch (e) { alert(e.message); }
  };
  if (!passed) document.getElementById('retryBtn').onclick = async () => {
    try {
      const levels = await API.get('/api/exam/levels');
      const meta = levels.find(l => l.id === lvl.id);
      startLevel(lvl.id, meta);
    } catch (e) { alert(e.message); }
  };
}

/* ---------------------------------------------------------------- certificate */

function drawStamp(doc, cx, cy, r) {
  doc.setDrawColor('#c79a3d');
  doc.setLineWidth(1.1); doc.circle(cx, cy, r, 'S');
  doc.setLineWidth(0.7); doc.circle(cx, cy, r - 10, 'S');
  doc.setLineWidth(0.5); doc.circle(cx, cy, r - 18, 'S');
  const text = 'PYBASICS \u2022 CERTIFIED \u2022 PYTHON FUNDAMENTALS \u2022 ';
  const chars = text.split('');
  const n = chars.length;
  doc.setFont('helvetica', 'bold'); doc.setFontSize(6.3); doc.setTextColor('#e7c877');
  chars.forEach((ch, i) => {
    const angle = -90 + (360 * i / n);
    const rad = angle * Math.PI / 180;
    const x = cx + (r - 5) * Math.cos(rad);
    const y = cy + (r - 5) * Math.sin(rad);
    doc.text(ch, x, y, { angle: -(angle - 90), align: 'center' });
  });
  doc.setDrawColor('#e7c877'); doc.setLineWidth(2);
  doc.line(cx - r * 0.22, cy + r * 0.02, cx - r * 0.05, cy + r * 0.2);
  doc.line(cx - r * 0.05, cy + r * 0.2, cx + r * 0.28, cy - r * 0.22);
}

function rasterizeToPng(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth || img.width;
      canvas.height = img.naturalHeight || img.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      try { resolve({ dataUrl: canvas.toDataURL('image/png'), w: canvas.width, h: canvas.height }); }
      catch (e) { reject(e); }
    };
    img.onerror = reject;
    img.src = url;
  });
}

async function savePdf(cert, sigUrl) {
  const btn = document.getElementById('printBtn');
  const originalLabel = btn.textContent;
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
    const body = 'Covering the fundamentals of Python \u2014 variables, data types, strings, lists, control flow, functions, dictionaries, error handling and list comprehensions \u2014 across five progressively longer levels.';
    const lines = doc.splitTextToSize(body, W - 200);
    doc.text(lines, W / 2, 250, { align: 'center' });
    doc.setFontSize(11); doc.setTextColor('#c79a3d');
    doc.text(`Issued ${cert.issued}      \u00b7      Best scores: ${cert.total_score}/${cert.total_questions}`, W / 2, H - 60, { align: 'center' });

    const signX = W / 2, lineY = H - 78, lineHalf = 65;
    if (sigUrl) {
      try {
        const raster = await rasterizeToPng(sigUrl);
        const maxW = 130, maxH = 34;
        const scale = Math.min(maxW / raster.w, maxH / raster.h, 1);
        const drawW = raster.w * scale, drawH = raster.h * scale;
        doc.addImage(raster.dataUrl, 'PNG', signX - drawW / 2, lineY - drawH - 4, drawW, drawH);
      } catch (e) { /* leave the line blank */ }
    }
    doc.setDrawColor('#28406b'); doc.setLineWidth(0.75);
    doc.line(signX - lineHalf, lineY, signX + lineHalf, lineY);
    doc.setFontSize(8.5); doc.setTextColor('#c79a3d'); doc.setFont('helvetica', 'normal');
    doc.text('Program Director', signX, lineY + 12, { align: 'center' });
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
    btn.disabled = false; btn.textContent = originalLabel;
  }
}

async function renderCertificate() {
  pageFooter.style.display = 'block';
  topbar.innerHTML = `
    <div class="topbar">
      <div><div class="brand">Py<em>Basics</em></div><div class="tagline">Certificate</div></div>
      <div class="topbar-right">${logoutUI()}</div>
    </div>`;
  wireLogout();
  app.innerHTML = `<div class="card"><p>Loading your certificate\u2026</p></div>`;
  let cert, sigResp;
  try {
    [cert, sigResp] = await Promise.all([API.get('/api/certificate'), API.get('/api/signature')]);
  } catch (e) {
    app.innerHTML = `<div class="card"><p class="auth-error show">${escapeHtml(e.message)}</p>
      <button class="ghost-btn" id="backLevelsBtn">Back to levels</button></div>`;
    document.getElementById('backLevelsBtn').onclick = () => { state.screen = 'levels'; render(); };
    return;
  }
  const sigUrl = sigResp.image || '/assets/default-signature.png';
  app.innerHTML = `
    <div class="cert">
      <div class="cert-kicker">This certifies that</div>
      <div class="cert-name">${escapeHtml(cert.full_name)}</div>
      <div class="cert-title">has completed the PyBasics Fundamentals Program</div>
      <div class="cert-body">Covering the fundamentals of Python \u2014 variables, data types, strings, lists, control flow, functions, dictionaries, error handling and list comprehensions \u2014 across five progressively longer levels, totaling ${cert.total_questions} questions.</div>
      <div class="cert-meta">
        <div class="cert-meta-col"><div class="cert-meta-label">Issued</div><div>${escapeHtml(cert.issued)}</div></div>
        <div class="cert-meta-col cert-sign-col">
          <img src="${sigUrl}" class="cert-sign-img" alt="Director signature">
          <div class="cert-sign-rule"></div>
          <div class="cert-meta-label">Program Director</div>
        </div>
        <div class="cert-meta-col"><div class="cert-meta-label">Best scores</div><div>${cert.total_score}/${cert.total_questions}</div></div>
      </div>
      <svg class="cert-stamp" viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg">
        <defs><path id="stampRing" d="M 80,80 m -60,0 a 60,60 0 1,1 120,0 a 60,60 0 1,1 -120,0" /></defs>
        <circle cx="80" cy="80" r="72" fill="none" stroke="var(--gold)" stroke-width="2"/>
        <circle cx="80" cy="80" r="60" fill="none" stroke="var(--gold)" stroke-width="1"/>
        <circle cx="80" cy="80" r="44" fill="none" stroke="var(--gold)" stroke-width="1" opacity="0.6"/>
        <text font-size="9.5" font-weight="700" letter-spacing="2.5" fill="var(--gold-soft)">
          <textPath href="#stampRing" startOffset="1%">PYBASICS \u2022 CERTIFIED \u2022 PYTHON FUNDAMENTALS \u2022</textPath>
        </text>
        <path d="M 60,82 L 74,94 L 102,64" fill="none" stroke="var(--gold-soft)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <div class="cert-sign-controls">
        <input type="file" id="sigUpload" accept="image/png,image/jpeg,image/svg+xml" style="display:none;">
        <button class="linklike" id="sigUploadBtn">Replace director signature</button>
        <button class="linklike" id="sigRemoveBtn">Remove signature</button>
      </div>
      <div class="cert-actions">
        <button class="primary-btn" id="printBtn" style="width:auto;">Save as PDF</button>
        <button class="ghost-btn" id="backBtn2">Back to levels</button>
      </div>
    </div>`;
  document.getElementById('backBtn2').onclick = () => { state.screen = 'levels'; render(); };
  document.getElementById('printBtn').onclick = () => savePdf(cert, sigUrl);
  document.getElementById('sigUploadBtn').onclick = () => document.getElementById('sigUpload').click();
  document.getElementById('sigUpload').addEventListener('change', async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    if (!/^image\/(png|jpeg|svg\+xml)$/.test(file.type)) { alert('Please choose a PNG, JPG, or SVG image.'); return; }
    if (file.size > 2 * 1024 * 1024) { alert('That image is a bit large \u2014 please use one under 2MB.'); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      try { await API.post('/api/signature', { image: reader.result }); render(); }
      catch (err) { alert(err.message); }
    };
    reader.readAsDataURL(file);
  });
  document.getElementById('sigRemoveBtn').onclick = async () => {
    try { await API.del('/api/signature'); render(); } catch (err) { alert(err.message); }
  };
}

boot();
