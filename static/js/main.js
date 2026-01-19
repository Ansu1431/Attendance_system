const video = document.getElementById('video');
const verifyBtn = document.getElementById('verify');
const result = document.getElementById('result');

// Initialize camera with better error handling
async function initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: 'user',
        width: { ideal: 1280 },
        height: { ideal: 720 }
      }
    });
    video.srcObject = stream;
    
    // Add success indicator
    verifyBtn.disabled = false;
    verifyBtn.innerHTML = '<i class="fas fa-check-circle me-2"></i>Verify & Mark Attendance';
  } catch (e) {
    showResult('Cannot access camera: ' + e.message + '. Please allow camera permissions.', false);
    verifyBtn.disabled = true;
    verifyBtn.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Camera Not Available';
  }
}

// Capture image as data URL
function captureDataUrl() {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.9);
}

// Show result with enhanced styling
function showResult(msg, ok) {
  result.classList.remove('d-none', 'alert-danger-modern', 'alert-success-modern');
  result.classList.add(ok ? 'alert-success-modern' : 'alert-danger-modern');
  
  // Add icon based on result
  const icon = ok ? '<i class="fas fa-check-circle me-2"></i>' : '<i class="fas fa-exclamation-circle me-2"></i>';
  result.innerHTML = icon + msg;
  
  // Auto-hide after 5 seconds for success messages
  if (ok) {
    setTimeout(() => {
      result.classList.add('d-none');
    }, 5000);
  }
}

// Verify button click handler
verifyBtn?.addEventListener('click', async () => {
  // Disable button during processing
  verifyBtn.disabled = true;
  verifyBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
  
  showResult('Capturing image and verifying...', true);
  
  const dataUrl = captureDataUrl();
  
  try {
    const resp = await fetch('/api/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ image: dataUrl })
    });
    
    const j = await resp.json();
    
    if (j.error) {
      showResult('Error: ' + j.error, false);
    } else if (j.match) {
      // Success animation
      result.style.transform = 'scale(1.05)';
      setTimeout(() => {
        result.style.transform = 'scale(1)';
      }, 200);
      
      showResult(`Success! Welcome ${j.name}! Your attendance has been recorded.`, true);
      
      // Success sound effect (optional - browser may block)
      try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
      } catch (e) {
        // Audio not available or blocked
      }
    } else {
      showResult('Face not recognized. Please make sure you are registered.', false);
    }
  } catch (e) {
    showResult('Request failed: ' + e.message, false);
  } finally {
    // Re-enable button
    verifyBtn.disabled = false;
    verifyBtn.innerHTML = '<i class="fas fa-check-circle me-2"></i>Verify & Mark Attendance';
  }
});

// Add video loaded event for better UX
video.addEventListener('loadedmetadata', () => {
  console.log('Video loaded:', video.videoWidth, 'x', video.videoHeight);
});

// Add error handling for video
video.addEventListener('error', (e) => {
  console.error('Video error:', e);
  showResult('Video stream error. Please refresh the page.', false);
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  initCamera();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (video.srcObject) {
    const tracks = video.srcObject.getTracks();
    tracks.forEach(track => track.stop());
  }
});
