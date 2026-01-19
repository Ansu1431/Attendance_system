from flask import Flask, request, render_template, jsonify, redirect, url_for, session, send_from_directory
import os
import io
import base64
import glob
import numpy as np
from datetime import datetime

# Try to import face_recognition; if not available, fall back to image-hash based matching
try:
    import face_recognition
    FACE_RECOG_AVAILABLE = True
except Exception as _e:
    FACE_RECOG_AVAILABLE = False
    print('face_recognition not available, falling back to image-hash matcher:', _e)
    from PIL import Image
    import imagehash

from PIL import Image as PILImage

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'change-me')

# Simple admin password (replace or set env var ADMIN_PASSWORD in production)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

BASE_DIR = os.path.dirname(__file__)
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
ATTENDANCE_CSV = os.path.join(BASE_DIR, 'attendance.csv')


def sanitize_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')


def load_known_faces():
    """Load known faces. If face_recognition is available return name->encoding (np.array).
    Otherwise return name->imagehash object (phash)."""
    encodings = {}
    for path in glob.glob(os.path.join(IMAGES_DIR, '*')):
        if os.path.isfile(path):
            filename = os.path.basename(path)
            name, _ = os.path.splitext(filename)
            try:
                if FACE_RECOG_AVAILABLE:
                    img = face_recognition.load_image_file(path)
                    faces = face_recognition.face_encodings(img)
                    if faces:
                        encodings[name] = faces[0]
                else:
                    pil = PILImage.open(path).convert('RGB')
                    encodings[name] = imagehash.phash(pil)
            except Exception as e:
                print(f"Skipping {path}: {e}")
    return encodings


# Global cache of known faces
KNOWN_FACES = load_known_faces()


def record_attendance(name: str):
    """Append an attendance record to CSV (name,date,time)."""
    try:
        ts = datetime.now()
        line = f'{name},{ts.date()},{ts.time().strftime("%H:%M:%S")}\n'
        with open(ATTENDANCE_CSV, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception as e:
        print('Failed to record attendance:', e)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/admin')
def admin_login():
    return render_template('admin_login.html')


@app.route('/admin/login', methods=['POST'])
def do_admin_login():
    password = request.form.get('password', '')
    if password == ADMIN_PASSWORD:
        session['admin'] = True
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html', error='Invalid password')


def _image_from_bytes(file_bytes):
    try:
        if FACE_RECOG_AVAILABLE:
            img = face_recognition.load_image_file(io.BytesIO(file_bytes))
            return img
        else:
            return PILImage.open(io.BytesIO(file_bytes)).convert('RGB')
    except Exception:
        return PILImage.open(io.BytesIO(file_bytes)).convert('RGB')


@app.route('/api/verify', methods=['POST'])
def api_verify():
    # Accept form-data file or JSON with base64 image
    file = request.files.get('image')
    img = None
    if file:
        img = _image_from_bytes(file.read())
    else:
        payload = request.get_json(silent=True) or {}
        b64 = payload.get('image')
        if b64:
            header, _, data = b64.partition(',')
            file_bytes = base64.b64decode(data or b64)
            img = _image_from_bytes(file_bytes)

    if img is None:
        return jsonify({'error': 'No image provided'}), 400

    # If face_recognition is available, use embeddings; otherwise use image-hash based approximate match
    if FACE_RECOG_AVAILABLE:
        faces = face_recognition.face_encodings(img)
        if not faces:
            return jsonify({'error': 'No face found'}), 400
        face = faces[0]
        names = list(KNOWN_FACES.keys())
        encs = list(KNOWN_FACES.values())
        if not encs:
            return jsonify({'error': 'No registered students'}), 400
        distances = face_recognition.face_distance(encs, face)
        best_idx = int(np.argmin(distances))
        match = distances[best_idx] < 0.5
        name = names[best_idx] if match else 'Unknown'
        if match:
            record_attendance(name)
        return jsonify({'name': name, 'match': bool(match), 'distance': float(distances[best_idx])})
    else:
        # img is a PIL Image
        ph = imagehash.phash(img)
        best = None
        best_dist = 999
        for n, h in KNOWN_FACES.items():
            d = ph - h
            if d < best_dist:
                best_dist = d
                best = n
        if best is None:
            return jsonify({'error': 'No registered students'}), 400
        match = best_dist <= 10
        if match:
            record_attendance(best)
        return jsonify({'name': best if match else 'Unknown', 'match': bool(match), 'distance': int(best_dist)})


@app.route('/api/admin/add_student', methods=['POST'])
def api_add_student():
    if not session.get('admin'):
        return jsonify({'error': 'unauthorized'}), 401
    name = request.form.get('name', '').strip()
    file = request.files.get('image')
    if not name:
        return jsonify({'error': 'name required'}), 400
    safe = sanitize_name(name)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    if file:
        ext = os.path.splitext(file.filename)[1] or '.png'
        dest = os.path.join(IMAGES_DIR, f"{safe}{ext}")
        file.save(dest)
    else:
        # no uploaded file: copy placeholder image so student has a thumbnail
        placeholder = os.path.join(BASE_DIR, 'static', 'img', 'placeholder.png')
        dest = os.path.join(IMAGES_DIR, f"{safe}.png")
        try:
            if os.path.exists(placeholder):
                import shutil
                shutil.copyfile(placeholder, dest)
            else:
                # create a tiny blank image as fallback
                from PIL import Image as PILImg
                img = PILImg.new('RGB', (200, 200), color=(200, 200, 200))
                img.save(dest)
        except Exception as e:
            print('Failed to create placeholder image:', e)
    # reload
    global KNOWN_FACES
    KNOWN_FACES = load_known_faces()
    return jsonify({'ok': True, 'students': list(KNOWN_FACES.keys())})


@app.route('/api/admin/remove_student', methods=['POST'])
def api_remove_student():
    if not session.get('admin'):
        return jsonify({'error': 'unauthorized'}), 401
    name = request.form.get('name', '')
    if not name:
        return jsonify({'error': 'name required'}), 400
    safe = sanitize_name(name)
    removed = False
    for path in glob.glob(os.path.join(IMAGES_DIR, f"{safe}.*")):
        try:
            os.remove(path)
            removed = True
        except Exception as e:
            print('remove error', e)
    global KNOWN_FACES
    KNOWN_FACES = load_known_faces()
    return jsonify({'ok': True, 'removed': removed, 'students': list(KNOWN_FACES.keys())})


@app.route('/images/<path:filename>')
def serve_image(filename):
    # Serve images from the images directory
    return send_from_directory(IMAGES_DIR, filename)


def read_attendance():
    rows = []
    if os.path.exists(ATTENDANCE_CSV):
        try:
            with open(ATTENDANCE_CSV, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        rows.append({'name': parts[0], 'date': parts[1], 'time': parts[2]})
        except Exception as e:
            print('Failed to read attendance:', e)
    return rows


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    # Build student list from actual files in IMAGES_DIR so we can show correct extensions
    students = []
    for path in sorted(glob.glob(os.path.join(IMAGES_DIR, '*'))):
        if os.path.isfile(path):
            filename = os.path.basename(path)
            name, _ext = os.path.splitext(filename)
            students.append({'name': name, 'filename': filename})
    attendance = read_attendance()
    return render_template('admin_dashboard.html', students=students, attendance=attendance)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

