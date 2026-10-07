import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, g, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

import questions as Q
from grader import run_submission, values_equal, py_repr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'pybasics.db')
COURSE_PATH = os.path.join(BASE_DIR, 'course.json')
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')

with open(COURSE_PATH, encoding='utf-8') as f:
    COURSE = json.load(f)

app = Flask(__name__, static_folder=None)
app.config['SECRET_KEY'] = os.environ.get('PYBASICS_SECRET_KEY', 'dev-secret-change-me')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# In-memory store of active exam attempts: {(user_id, level_id): {...}}
# Lost on server restart -- fine for a learning tool; move to Redis/DB for production.
ACTIVE_ATTEMPTS = {}


# --------------------------------------------------------------------------- DB

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        course_start_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS course_progress (
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        day INTEGER NOT NULL,
        completed_at INTEGER NOT NULL,
        PRIMARY KEY (user_id, day)
    );
    CREATE TABLE IF NOT EXISTS exam_progress (
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        level_id INTEGER NOT NULL,
        best_score INTEGER NOT NULL DEFAULT 0,
        total INTEGER NOT NULL DEFAULT 0,
        passed INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER NOT NULL,
        PRIMARY KEY (user_id, level_id)
    );
    CREATE TABLE IF NOT EXISTS violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        level_id INTEGER,
        reason TEXT,
        created_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS signature (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        image_data_url TEXT
    );
    ''')
    db.commit()
    db.close()


# --------------------------------------------------------------------------- helpers

def now_ms():
    return int(time.time() * 1000)


def start_of_day_ms(ms):
    d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    d = d.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(d.timestamp() * 1000)


def days_between(a_ms, b_ms):
    return round((start_of_day_ms(b_ms) - start_of_day_ms(a_ms)) / 86400000)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'not logged in'}), 401
        return fn(*args, **kwargs)
    return wrapper


def current_user():
    db = get_db()
    row = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return row


def course_progress(user_id):
    db = get_db()
    rows = db.execute('SELECT day FROM course_progress WHERE user_id = ?', (user_id,)).fetchall()
    return sorted(r['day'] for r in rows)


def unlocked_day_count(user_row):
    return min(len(COURSE), days_between(user_row['course_start_at'], now_ms()) + 1)


def course_complete(user_id):
    return len(course_progress(user_id)) >= len(COURSE)


def exam_progress_map(user_id):
    db = get_db()
    rows = db.execute('SELECT * FROM exam_progress WHERE user_id = ?', (user_id,)).fetchall()
    return {r['level_id']: dict(r) for r in rows}


def level_unlocked(level_id, progress_map):
    if level_id == 1:
        return True
    return bool(progress_map.get(level_id - 1, {}).get('passed'))


# --------------------------------------------------------------------------- static frontend

@app.get('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.get('/css/<path:path>')
def css(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), path)


@app.get('/js/<path:path>')
def js(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), path)


@app.get('/assets/<path:path>')
def assets(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'assets'), path)


# --------------------------------------------------------------------------- auth

@app.post('/api/auth/signup')
def signup():
    data = request.get_json(force=True)
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    full_name = ' '.join((data.get('full_name') or '').split())

    if not username or not password:
        return jsonify({'error': 'Enter a username and password.'}), 400
    if len(full_name.split()) < 2:
        return jsonify({'error': "Please enter your full name (first and last name) \u2014 it will appear on your certificate."}), 400
    if len(full_name) > 60:
        return jsonify({'error': 'That name is too long \u2014 please keep it under 60 characters.'}), 400

    db = get_db()
    existing = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existing:
        return jsonify({'error': 'That username is already taken.'}), 400

    ts = now_ms()
    db.execute(
        'INSERT INTO users (username, password_hash, full_name, created_at, course_start_at) VALUES (?, ?, ?, ?, ?)',
        (username, generate_password_hash(password), full_name, ts, ts))
    db.commit()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    session['user_id'] = user['id']
    return jsonify({'username': user['username'], 'full_name': user['full_name'], 'course_complete': course_complete(user['id'])})


@app.post('/api/auth/login')
def login():
    data = request.get_json(force=True)
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Incorrect username or password.'}), 401
    session['user_id'] = user['id']
    return jsonify({'username': user['username'], 'full_name': user['full_name'], 'course_complete': course_complete(user['id'])})


@app.post('/api/auth/logout')
def logout():
    session.clear()
    return jsonify({'ok': True})


@app.get('/api/auth/me')
@login_required
def me():
    user = current_user()
    return jsonify({'username': user['username'], 'full_name': user['full_name'],
                     'course_complete': course_complete(user['id'])})


# --------------------------------------------------------------------------- course

@app.get('/api/course')
@login_required
def course_list():
    user = current_user()
    unlocked = unlocked_day_count(user)
    done = set(course_progress(user['id']))
    return jsonify([
        {'day': l['day'], 'title': l['title'], 'unlocked': l['day'] <= unlocked, 'completed': l['day'] in done}
        for l in COURSE
    ])


@app.get('/api/course/<int:day>')
@login_required
def course_detail(day):
    user = current_user()
    lesson = next((l for l in COURSE if l['day'] == day), None)
    if not lesson:
        return jsonify({'error': 'no such lesson'}), 404
    if day > unlocked_day_count(user):
        return jsonify({'error': 'This lesson has not unlocked yet.'}), 403
    done = day in course_progress(user['id'])
    return jsonify({
        'day': lesson['day'], 'title': lesson['title'], 'read': lesson['read'], 'code': lesson['code'],
        'codeNote': lesson['codeNote'], 'query': lesson['query'], 'completed': done,
        'quiz': [{'q': x['q'], 'options': x['options']} for x in lesson['quiz']],
    })


@app.post('/api/course/<int:day>/answer')
@login_required
def course_answer(day):
    user = current_user()
    if day > unlocked_day_count(user):
        return jsonify({'error': 'This lesson has not unlocked yet.'}), 403
    lesson = next((l for l in COURSE if l['day'] == day), None)
    if not lesson:
        return jsonify({'error': 'no such lesson'}), 404
    data = request.get_json(force=True)
    q_index = data.get('qIndex')
    selected = data.get('selected')
    if q_index is None or not (0 <= q_index < len(lesson['quiz'])):
        return jsonify({'error': 'bad question index'}), 400
    item = lesson['quiz'][q_index]
    correct = selected == item['correct']
    return jsonify({'correct': correct, 'correctIndex': item['correct'], 'explain': item['explain']})


@app.post('/api/course/<int:day>/complete')
@login_required
def course_complete_day(day):
    """Marks a lesson complete. Trusts the client to have finished the practice
    quiz first (it's formative practice, not the graded exam -- see README)."""
    user = current_user()
    if day > unlocked_day_count(user):
        return jsonify({'error': 'This lesson has not unlocked yet.'}), 403
    db = get_db()
    db.execute('INSERT OR IGNORE INTO course_progress (user_id, day, completed_at) VALUES (?, ?, ?)',
               (user['id'], day, now_ms()))
    db.commit()
    return jsonify({'ok': True, 'courseComplete': course_complete(user['id'])})


# --------------------------------------------------------------------------- exam

@app.get('/api/exam/levels')
@login_required
def exam_levels():
    user = current_user()
    if not course_complete(user['id']):
        return jsonify({'error': 'Complete the 30-day course first.'}), 403
    progress = exam_progress_map(user['id'])
    out = []
    for lvl in Q.LEVELS:
        p = progress.get(lvl['id'])
        out.append({
            'id': lvl['id'], 'name': lvl['name'], 'difficulty': lvl['difficulty'],
            'count': lvl['count'], 'type': lvl['type'], 'unlocked': level_unlocked(lvl['id'], progress),
            'best': p['best_score'] if p else None, 'total': p['total'] if p else lvl['count'],
            'passed': bool(p and p['passed']),
        })
    return jsonify(out)


@app.post('/api/exam/level/<int:level_id>/start')
@login_required
def exam_start(level_id):
    user = current_user()
    if not course_complete(user['id']):
        return jsonify({'error': 'Complete the 30-day course first.'}), 403
    lvl = Q.level_by_id(level_id)
    if not lvl:
        return jsonify({'error': 'no such level'}), 404
    progress = exam_progress_map(user['id'])
    if not level_unlocked(level_id, progress):
        return jsonify({'error': 'This level is locked.'}), 403

    questions = Q.generate_level_questions(lvl)
    ACTIVE_ATTEMPTS[(user['id'], level_id)] = {
        'questions': questions, 'answers': [None] * len(questions),
        'first_try_correct': [None] * len(questions), 'started_at': now_ms(),
    }
    public = [Q.public_question(q) for q in questions]
    return jsonify({'type': lvl['type'], 'count': lvl['count'], 'questions': public})


def _get_attempt(user_id, level_id):
    return ACTIVE_ATTEMPTS.get((user_id, level_id))


@app.post('/api/exam/level/<int:level_id>/mcq/<int:q_index>/answer')
@login_required
def exam_mcq_answer(level_id, q_index):
    user = current_user()
    attempt = _get_attempt(user['id'], level_id)
    if not attempt or not (0 <= q_index < len(attempt['questions'])):
        return jsonify({'error': 'No active attempt for this question. Start the level again.'}), 409
    data = request.get_json(force=True)
    selected = data.get('selected')
    item = attempt['questions'][q_index]
    correct = selected == item['correct']
    if attempt['first_try_correct'][q_index] is None:
        attempt['first_try_correct'][q_index] = correct
    attempt['answers'][q_index] = selected
    return jsonify({'correct': correct, 'correctIndex': item['correct'], 'explain': item['explain']})


@app.post('/api/exam/level/<int:level_id>/code/<int:q_index>/check')
@login_required
def exam_code_check(level_id, q_index):
    user = current_user()
    attempt = _get_attempt(user['id'], level_id)
    if not attempt or not (0 <= q_index < len(attempt['questions'])):
        return jsonify({'error': 'No active attempt for this question. Start the level again.'}), 409
    data = request.get_json(force=True)
    code = data.get('code') or ''
    item = attempt['questions'][q_index]
    env, err = run_submission(code)
    rows = []
    all_ok = not err
    if not err:
        for k, want in item['expected'].items():
            got = env.get(k)
            ok = k in env and values_equal(got, want)
            rows.append({'name': k, 'ok': ok, 'got': py_repr(got) if k in env else '(not set)', 'want': py_repr(want)})
            all_ok = all_ok and ok
    if attempt['first_try_correct'][q_index] is None:
        attempt['first_try_correct'][q_index] = all_ok
    explain = item['explain'] if all_ok else None
    return jsonify({'correct': all_ok, 'error': err, 'rows': rows, 'explain': explain})


@app.post('/api/exam/level/<int:level_id>/finish')
@login_required
def exam_finish(level_id):
    user = current_user()
    lvl = Q.level_by_id(level_id)
    attempt = _get_attempt(user['id'], level_id)
    if not attempt or not lvl:
        return jsonify({'error': 'No active attempt. Start the level again.'}), 409
    total = len(attempt['questions'])
    score = sum(1 for c in attempt['first_try_correct'] if c)
    passed = score / total >= Q.PASS_RATIO
    db = get_db()
    existing = db.execute('SELECT best_score FROM exam_progress WHERE user_id = ? AND level_id = ?',
                           (user['id'], level_id)).fetchone()
    best = max(score, existing['best_score']) if existing else score
    was_passed = bool(existing and db.execute(
        'SELECT passed FROM exam_progress WHERE user_id=? AND level_id=?', (user['id'], level_id)
    ).fetchone()['passed'])
    db.execute('''INSERT INTO exam_progress (user_id, level_id, best_score, total, passed, updated_at)
                  VALUES (?, ?, ?, ?, ?, ?)
                  ON CONFLICT(user_id, level_id) DO UPDATE SET
                    best_score = excluded.best_score, total = excluded.total,
                    passed = MAX(exam_progress.passed, excluded.passed), updated_at = excluded.updated_at''',
               (user['id'], level_id, best, total, int(passed or was_passed), now_ms()))
    db.commit()
    del ACTIVE_ATTEMPTS[(user['id'], level_id)]
    return jsonify({'score': score, 'total': total, 'passed': passed or was_passed})


@app.post('/api/exam/violation')
@login_required
def exam_violation():
    user = current_user()
    data = request.get_json(force=True)
    level_id = data.get('levelId')
    reason = data.get('reason', 'left the page')
    if (user['id'], level_id) in ACTIVE_ATTEMPTS:
        del ACTIVE_ATTEMPTS[(user['id'], level_id)]
    db = get_db()
    db.execute('INSERT INTO violations (user_id, level_id, reason, created_at) VALUES (?, ?, ?, ?)',
               (user['id'], level_id, reason, now_ms()))
    db.commit()
    session.clear()
    return jsonify({'ok': True})


# --------------------------------------------------------------------------- certificate & signature

@app.get('/api/certificate')
@login_required
def certificate():
    user = current_user()
    progress = exam_progress_map(user['id'])
    if len(progress) < len(Q.LEVELS) or not all(p['passed'] for p in progress.values()):
        return jsonify({'error': 'Not all levels are passed yet.'}), 403
    levels = [{'id': l['id'], 'name': l['name'], 'best': progress[l['id']]['best_score'], 'total': progress[l['id']]['total']}
              for l in Q.LEVELS]
    now = datetime.now(timezone.utc)
    return jsonify({
        'full_name': user['full_name'],
        'issued': f"{now:%B} {now.day}, {now:%Y}",
        'levels': levels,
        'total_score': sum(l['best'] for l in levels),
        'total_questions': sum(l['total'] for l in levels),
    })


@app.get('/api/signature')
def get_signature():
    db = get_db()
    row = db.execute('SELECT image_data_url FROM signature WHERE id = 1').fetchone()
    return jsonify({'image': row['image_data_url'] if row else None})


@app.post('/api/signature')
@login_required
def set_signature():
    data = request.get_json(force=True)
    image = data.get('image')
    if not image or not image.startswith('data:image/'):
        return jsonify({'error': 'Expected a data:image/... URL'}), 400
    if len(image) > 3_000_000:
        return jsonify({'error': 'Image too large'}), 400
    db = get_db()
    db.execute('INSERT INTO signature (id, image_data_url) VALUES (1, ?) '
               'ON CONFLICT(id) DO UPDATE SET image_data_url = excluded.image_data_url', (image,))
    db.commit()
    return jsonify({'ok': True})


@app.delete('/api/signature')
@login_required
def clear_signature():
    db = get_db()
    db.execute('INSERT INTO signature (id, image_data_url) VALUES (1, NULL) '
               'ON CONFLICT(id) DO UPDATE SET image_data_url = NULL')
    db.commit()
    return jsonify({'ok': True})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
