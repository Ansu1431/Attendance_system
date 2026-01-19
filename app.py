from flask import Flask, request, render_template, jsonify, redirect, url_for, session, send_from_directory, flash
from flask_mail import Mail, Message
import os
import io
import base64
import glob
import numpy as np
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
import secrets

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

# Define paths first
BASE_DIR = os.path.dirname(__file__)
PASSWORD_FILE = os.path.join(BASE_DIR, '.admin_password')

# Simple admin password (replace or set env var ADMIN_PASSWORD in production)
# Check for password file first, then env var, then default
def get_admin_password():
    if os.path.exists(PASSWORD_FILE):
        try:
            with open(PASSWORD_FILE, 'r') as f:
                return f.read().strip()
        except:
            pass
    return os.environ.get('ADMIN_PASSWORD', 'admin123')

def save_admin_password(password):
    """Save admin password to file"""
    try:
        with open(PASSWORD_FILE, 'w') as f:
            f.write(password.strip())
        return True
    except Exception as e:
        print(f'Error saving password: {e}')
        return False

ADMIN_PASSWORD = get_admin_password()

# Try to load from config file first, then environment variables
# Check root directory first (for backward compatibility), then config directory
try:
    # Try root directory first
    import email_config as email_cfg
    ADMIN_EMAIL = getattr(email_cfg, 'ADMIN_EMAIL', os.environ.get('ADMIN_EMAIL', 'admin@example.com'))
    ADMIN_NAME = getattr(email_cfg, 'ADMIN_NAME', os.environ.get('ADMIN_NAME', 'Admin'))
    app.config['MAIL_SERVER'] = getattr(email_cfg, 'MAIL_SERVER', os.environ.get('MAIL_SERVER', 'smtp.gmail.com'))
    app.config['MAIL_PORT'] = int(getattr(email_cfg, 'MAIL_PORT', os.environ.get('MAIL_PORT', 587)))
    app.config['MAIL_USE_TLS'] = getattr(email_cfg, 'MAIL_USE_TLS', True) if hasattr(email_cfg, 'MAIL_USE_TLS') else (os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true')
    app.config['MAIL_USE_SSL'] = getattr(email_cfg, 'MAIL_USE_SSL', False) if hasattr(email_cfg, 'MAIL_USE_SSL') else (os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true')
    app.config['MAIL_USERNAME'] = getattr(email_cfg, 'MAIL_USERNAME', os.environ.get('MAIL_USERNAME', ''))
    app.config['MAIL_PASSWORD'] = getattr(email_cfg, 'MAIL_PASSWORD', os.environ.get('MAIL_PASSWORD', ''))
    app.config['MAIL_DEFAULT_SENDER'] = getattr(email_cfg, 'MAIL_DEFAULT_SENDER', os.environ.get('MAIL_DEFAULT_SENDER', ADMIN_EMAIL))
    print("[OK] Email configuration loaded from email_config.py")
except ImportError:
    # Try config directory
    try:
        import sys
        config_path = os.path.join(BASE_DIR, 'config')
        if config_path not in sys.path:
            sys.path.insert(0, config_path)
        import email_config as email_cfg
        ADMIN_EMAIL = getattr(email_cfg, 'ADMIN_EMAIL', os.environ.get('ADMIN_EMAIL', 'admin@example.com'))
        ADMIN_NAME = getattr(email_cfg, 'ADMIN_NAME', os.environ.get('ADMIN_NAME', 'Admin'))
        app.config['MAIL_SERVER'] = getattr(email_cfg, 'MAIL_SERVER', os.environ.get('MAIL_SERVER', 'smtp.gmail.com'))
        app.config['MAIL_PORT'] = int(getattr(email_cfg, 'MAIL_PORT', os.environ.get('MAIL_PORT', 587)))
        app.config['MAIL_USE_TLS'] = getattr(email_cfg, 'MAIL_USE_TLS', True) if hasattr(email_cfg, 'MAIL_USE_TLS') else (os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true')
        app.config['MAIL_USE_SSL'] = getattr(email_cfg, 'MAIL_USE_SSL', False) if hasattr(email_cfg, 'MAIL_USE_SSL') else (os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true')
        app.config['MAIL_USERNAME'] = getattr(email_cfg, 'MAIL_USERNAME', os.environ.get('MAIL_USERNAME', ''))
        app.config['MAIL_PASSWORD'] = getattr(email_cfg, 'MAIL_PASSWORD', os.environ.get('MAIL_PASSWORD', ''))
        app.config['MAIL_DEFAULT_SENDER'] = getattr(email_cfg, 'MAIL_DEFAULT_SENDER', os.environ.get('MAIL_DEFAULT_SENDER', ADMIN_EMAIL))
        print("[OK] Email configuration loaded from config/email_config.py")
    except ImportError:
    # Load email config from file
    ADMIN_EMAIL = ADMIN_EMAIL if 'ADMIN_EMAIL' in locals() else os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    ADMIN_NAME = ADMIN_NAME if 'ADMIN_NAME' in locals() else os.environ.get('ADMIN_NAME', 'Admin')
    app.config['MAIL_SERVER'] = MAIL_SERVER if 'MAIL_SERVER' in locals() else os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(MAIL_PORT if 'MAIL_PORT' in locals() else os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = MAIL_USE_TLS if 'MAIL_USE_TLS' in locals() else os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USE_SSL'] = MAIL_USE_SSL if 'MAIL_USE_SSL' in locals() else os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    app.config['MAIL_USERNAME'] = MAIL_USERNAME if 'MAIL_USERNAME' in locals() else os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = MAIL_PASSWORD if 'MAIL_PASSWORD' in locals() else os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER if 'MAIL_DEFAULT_SENDER' in locals() else os.environ.get('MAIL_DEFAULT_SENDER', ADMIN_EMAIL)
    print("[OK] Email configuration loaded from email_config.py")
except ImportError:
    # Fall back to environment variables
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    ADMIN_NAME = os.environ.get('ADMIN_NAME', 'Admin')
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', ADMIN_EMAIL)
    print("[INFO] Using environment variables for email configuration (or create email_config.py)")

# Initialize Flask-Mail
mail = Mail(app)

# Token serializer for password reset
serializer = URLSafeTimedSerializer(app.secret_key)

IMAGES_DIR = os.path.join(BASE_DIR, 'static', 'images')
ATTENDANCE_CSV = os.path.join(BASE_DIR, 'data', 'attendance.csv')


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
    current_password = get_admin_password()
    if password == current_password:
        session['admin'] = True
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html', error='Invalid password')


@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        # Check if email matches admin email
        if email.lower() == ADMIN_EMAIL.lower():
            # Generate reset token (valid for 1 hour)
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            
            # Send email
            try:
                # Test email configuration
                if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
                    raise ValueError('Email username or password not configured')
                
                msg = Message(
                    subject='Password Reset Request - Attendance System',
                    recipients=[ADMIN_EMAIL],
                    html=render_template('emails/email_reset_password.html', 
                                       reset_url=reset_url, 
                                       admin_name=ADMIN_NAME,
                                       expiry_hours=1)
                )
                mail.send(msg)
                print(f"[SUCCESS] Password reset email sent to {ADMIN_EMAIL}")
                return render_template('forgot_password.html', 
                                     success='Password reset link has been sent to your email address. Please check your inbox.')
            except Exception as e:
                error_msg = str(e)
                print(f'[ERROR] Email sending failed: {error_msg}')
                print(f'[DEBUG] Mail config - Server: {app.config.get("MAIL_SERVER")}, Port: {app.config.get("MAIL_PORT")}')
                print(f'[DEBUG] Mail config - Username: {app.config.get("MAIL_USERNAME")}, TLS: {app.config.get("MAIL_USE_TLS")}')
                
                # Provide more helpful error message
                if 'authentication failed' in error_msg.lower() or 'invalid credentials' in error_msg.lower():
                    error_display = 'Email authentication failed. For Gmail, you need to use an App Password instead of your regular password. Please check EMAIL_SETUP.md for instructions.'
                elif '535' in error_msg or 'smtp' in error_msg.lower():
                    error_display = f'SMTP error: {error_msg}. Please verify your email credentials and SMTP settings.'
                else:
                    error_display = f'Failed to send email: {error_msg}. Please check your email configuration.'
                
                return render_template('forgot_password.html', error=error_display)
        else:
            # Don't reveal if email exists or not (security best practice)
            return render_template('forgot_password.html', 
                                 success='If the email address exists, a password reset link has been sent.')
    
    return render_template('forgot_password.html')


@app.route('/admin/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Verify token (valid for 1 hour)
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception as e:
        return render_template('reset_password.html', error='Invalid or expired reset link. Please request a new one.', invalid_token=True)
    
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not new_password:
            return render_template('reset_password.html', error='Password cannot be empty.', token=token)
        
        if new_password != confirm_password:
            return render_template('reset_password.html', error='Passwords do not match.', token=token)
        
        if len(new_password) < 6:
            return render_template('reset_password.html', error='Password must be at least 6 characters long.', token=token)
        
        # Update password
        if save_admin_password(new_password):
            global ADMIN_PASSWORD
            ADMIN_PASSWORD = new_password
            return render_template('reset_password.html', 
                                 success='Password has been successfully reset! You can now login with your new password.',
                                 token=None, reset_success=True)
        else:
            return render_template('reset_password.html', 
                                 error='Failed to save password. Please contact your system administrator.',
                                 token=token)
    
    if 'reset_success' in request.args:
        return render_template('reset_password.html', 
                             success='Password reset successful! You can now login with your new password.',
                             token=None, reset_success=True)
    return render_template('reset_password.html', token=token)


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

