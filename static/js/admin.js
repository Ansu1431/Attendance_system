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

  function showResult(message, isSuccess) {
    addResult.innerHTML = '';
    addResult.className = 'mt-3 alert-modern ' + (isSuccess ? 'alert-success-modern' : 'alert-danger-modern');
    const icon = isSuccess ? '<i class="fas fa-check-circle me-2"></i>' : '<i class="fas fa-exclamation-circle me-2"></i>';
    addResult.innerHTML = icon + message;
    addResult.classList.remove('d-none');
  }

  async function startCamera() {
    if (stream) return;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      });
      el(webcamVideoId).srcObject = stream;
      el(webcamContainerId).classList.remove('d-none');
      el(webcamToggleBtnId).innerHTML = '<i class="fas fa-stop me-2"></i>Stop Webcam';
      showResult('Camera started. Position the student and click Capture Photo.', true);
    } catch (e) {
      showResult('Camera failed: ' + e.message, false);
    }
  }

  function stopCamera() {
    if (!stream) return;
    stream.getTracks().forEach(t => t.stop());
    stream = null;
    el(webcamVideoId).srcObject = null;
    el(webcamContainerId).classList.add('d-none');
    el(webcamToggleBtnId).innerHTML = '<i class="fas fa-video me-2"></i>Use Webcam';
    showResult('Camera stopped.', true);
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
    if (!stream) {
      showResult('Please start the webcam first.', false);
      return;
    }
    
    showResult('Capturing image...', true);
    const blob = await captureImage();
    if (blob) {
      capturedBlob = blob;
      const url = URL.createObjectURL(blob);
      const img = el(webcamPreviewId);
      img.src = url;
      img.classList.remove('d-none');
      showResult('Photo captured! Fill in the name and click Add Student.', true);
    } else {
      showResult('Capture failed. Please try again.', false);
    }
  }

  async function onFormSubmit(e) {
    e.preventDefault();
    const nameInput = addForm.querySelector('[name="name"]');
    const name = nameInput.value.trim();
    
    if (!name) {
      showResult('Please enter a student name.', false);
      return;
    }

    showResult('Uploading student data...', true);
    
    const fd = new FormData();
    fd.append('name', name);
    
    const fileInput = addForm.querySelector('[name="image"]');
    if (fileInput && fileInput.files && fileInput.files.length > 0) {
      fd.append('image', fileInput.files[0]);
    } else if (capturedBlob) {
      const filename = (name || 'student') + '.jpg';
      fd.append('image', new File([capturedBlob], filename, { type: 'image/jpeg' }));
    }
    // Allow submission without image (placeholder will be used)

    try {
      const submitBtn = addForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Adding...';

      const resp = await fetch('/api/admin/add_student', { method: 'POST', body: fd });
      const j = await resp.json();
      
      if (j.ok) {
        showResult(`Student "${name}" added successfully!`, true);
        // Clear form
        nameInput.value = '';
        if (fileInput) fileInput.value = '';
        capturedBlob = null;
        const img = el(webcamPreviewId);
        img.src = '';
        img.classList.add('d-none');
        
        setTimeout(() => location.reload(), 1500);
      } else {
        showResult(j.error || 'Error adding student', false);
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-plus-circle me-2"></i>Add Student';
      }
    } catch (err) {
      showResult('Upload failed: ' + err.message, false);
      const submitBtn = addForm.querySelector('button[type="submit"]');
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-plus-circle me-2"></i>Add Student';
    }
  }

  function attachRemoveHandlers() {
    removeButtons().forEach(btn => {
      btn.addEventListener('click', async () => {
        const name = btn.dataset.name;
        if (!confirm(`Are you sure you want to remove "${name}"? This action cannot be undone.`)) return;
        
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        
        const fd = new FormData(); 
        fd.append('name', name);
        
        try {
          const resp = await fetch('/api/admin/remove_student', { method: 'POST', body: fd });
          const j = await resp.json();
          if (j.ok) {
            // Show success message
            const row = btn.closest('tr');
            row.style.opacity = '0.5';
            row.style.transition = 'opacity 0.3s';
            setTimeout(() => location.reload(), 500);
          } else {
            alert('Error removing student');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-trash me-1"></i>Remove';
          }
        } catch (e) {
          alert('Request failed: ' + e.message);
          btn.disabled = false;
          btn.innerHTML = '<i class="fas fa-trash me-1"></i>Remove';
        }
      });
    });
  }

  // Setup webcam UI controls (inject if not present)
  function setupWebcamUI() {
    const container = document.createElement('div');
    container.className = 'mt-4';
    container.innerHTML = `
      <div class="card-modern">
        <div class="card-header">
          <h6 class="mb-0">
            <i class="fas fa-camera me-2"></i>Capture from Webcam
          </h6>
        </div>
        <div class="card-body">
          <div class="mb-3">
            <button id="${webcamToggleBtnId}" class="btn btn-modern btn-sm me-2">
              <i class="fas fa-video me-2"></i>Use Webcam
            </button>
            <button id="${webcamCaptureBtnId}" class="btn btn-modern btn-success-modern btn-sm">
              <i class="fas fa-camera me-2"></i>Capture Photo
            </button>
          </div>
          <div id="${webcamContainerId}" class="d-none">
            <div class="video-wrap mb-3">
              <video id="${webcamVideoId}" autoplay playsinline muted></video>
            </div>
            <div class="text-center">
              <img id="${webcamPreviewId}" class="d-none rounded shadow" 
                   style="width:200px; height:150px; object-fit:cover; border:3px solid rgba(255,255,255,0.3);" />
            </div>
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
      } else {
        stopCamera();
      }
    });

    capture.addEventListener('click', onCaptureClicked);
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
  });

  // Initialize
  if (addForm) {
    addForm.addEventListener('submit', onFormSubmit);
    setupWebcamUI();
  }
  attachRemoveHandlers();
})();
