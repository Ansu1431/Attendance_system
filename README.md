# Attendance frontend + simple Flask backend

This adds a minimal Flask web frontend to the existing project so users can mark attendance by verifying themselves using the webcam. An admin UI allows adding/removing students.

Files added:

- `app.py` - Flask application exposing verification and admin endpoints and serving the frontend.
- `templates/index.html` - Student-facing page that captures webcam image and verifies.
- `templates/admin_login.html` - Admin login page.
- `templates/admin_dashboard.html` - Admin page to add/remove students.
- `requirements.txt` - Python dependencies.

How it works

- Student page captures a snapshot as a base64 JPEG and POSTs it to `/api/verify`.
- The server compares the captured face with images placed in the `images/` directory.
- Admin can login (password from `ADMIN_PASSWORD` env var, default `admin123`) and add a student (upload name + image) or remove them.

Run locally (Windows PowerShell):

```powershell
python -m pip install -r requirements.txt
setx ADMIN_PASSWORD "yourpassword"  # optional
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

Notes & next steps

- This is a minimal implementation to get you started. For production use: secure the admin endpoint, persist attendance records, and add robust error handling.
- The system uses one reference image per student stored in `images/`.
