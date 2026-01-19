// Admin dashboard JS: handle webcam capture, add student, and remove student actions
(function() {
  const addForm = document.getElementById('addForm');
  const addResult = document.getElementById('addResult');
  const removeButtons = () => Array.from(document.querySelectorAll('.remove'));

  // Webcam elements
  const webcamToggleBtnId = 'webcamToggle';
  const webcamContainerId = 'webcamContainer';
  const webcamVideoId = 'webcamVideo';
  const webcamCaptureBtnId = 'webcamCapture';
  const webcamPreviewId = 'webcamPreview';

  let stream = null;
  let capturedBlob = null;

  function el(id) { return document.getElementById(id); }

  async function startCamera() {
    if (stream) return;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      el(webcamVideoId).srcObject = stream;
      el(webcamContainerId).classList.remove('d-none');
    } catch (e) {
      addResult.textContent = 'Camera failed: ' + e.message;
    }
  }

  function stopCamera() {
    if (!stream) return;
    stream.getTracks().forEach(t => t.stop());
    stream = null;
    el(webcamVideoId).srcObject = null;
    el(webcamContainerId).classList.add('d-none');
  }

  function captureImage() {
    const video = el(webcamVideoId);
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise(resolve => canvas.toBlob(blob => resolve(blob), 'image/jpeg', 0.9));
  }

  async function onCaptureClicked(e) {
    e.preventDefault();
    addResult.textContent = 'Capturing...';
    const blob = await captureImage();
    if (blob) {
      capturedBlob = blob;
      const url = URL.createObjectURL(blob);
      const img = el(webcamPreviewId);
      img.src = url;
      img.classList.remove('d-none');
      addResult.textContent = 'Captured — fill name and click Add Student.';
      // stopCamera(); // keep camera running for more captures
    } else {
      addResult.textContent = 'Capture failed';
    }
  }

  async function onFormSubmit(e) {
    e.preventDefault();
    addResult.textContent = 'Uploading...';
    const fd = new FormData();
    const name = addForm.querySelector('[name="name"]').value;
    fd.append('name', name);
    const fileInput = addForm.querySelector('[name="image"]');
    if (fileInput && fileInput.files && fileInput.files.length > 0) {
      fd.append('image', fileInput.files[0]);
    } else if (capturedBlob) {
      const filename = (name || 'student') + '.jpg';
      fd.append('image', new File([capturedBlob], filename, { type: 'image/jpeg' }));
    } else {
      addResult.textContent = 'Please provide an image (upload or capture).';
      return;
    }

    try {
      const resp = await fetch('/api/admin/add_student', { method: 'POST', body: fd });
      const j = await resp.json();
      if (j.ok) {
        addResult.textContent = 'Added successfully';
        setTimeout(() => location.reload(), 600);
      } else {
        addResult.textContent = j.error || 'Error adding student';
      }
    } catch (err) {
      addResult.textContent = 'Upload failed: ' + err.message;
    }
  }

  function attachRemoveHandlers() {
    removeButtons().forEach(btn => {
      btn.addEventListener('click', async () => {
        const name = btn.dataset.name;
        if (!confirm('Remove ' + name + '?')) return;
        const fd = new FormData(); fd.append('name', name);
        const resp = await fetch('/api/admin/remove_student', { method: 'POST', body: fd });
        const j = await resp.json();
        if (j.ok) location.reload(); else alert('Error');
      });
    });
  }

  // Setup webcam UI controls (inject if not present)
  function setupWebcamUI() {
    const container = document.createElement('div');
    container.className = 'mt-3';
    container.innerHTML = `
      <div class="card">
        <div class="card-body">
          <h6 class="card-title">Capture from Webcam</h6>
          <div class="mb-2">
            <button id="${webcamToggleBtnId}" class="btn btn-outline-primary btn-sm">Use Webcam</button>
            <button id="${webcamCaptureBtnId}" class="btn btn-success btn-sm ms-2">Capture Photo</button>
          </div>
          <div id="${webcamContainerId}" class="d-none">
            <video id="${webcamVideoId}" autoplay playsinline muted style="width:100%; max-height:320px; background:#000"></video>
            <img id="${webcamPreviewId}" class="mt-2 d-none" style="width:160px; height:120px; object-fit:cover; border-radius:6px" />
          </div>
        </div>
      </div>
    `;
    addForm.parentNode.insertBefore(container, addForm.nextSibling);

    const toggle = el(webcamToggleBtnId);
    const capture = el(webcamCaptureBtnId);

    toggle.addEventListener('click', async (ev) => {
      if (!stream) {
        await startCamera();
        toggle.textContent = 'Stop Webcam';
      } else {
        stopCamera();
        toggle.textContent = 'Use Webcam';
      }
    });

    capture.addEventListener('click', onCaptureClicked);
  }

  // initialize
  if (addForm) {
    addForm.addEventListener('submit', onFormSubmit);
    setupWebcamUI();
  }
  attachRemoveHandlers();
})();
