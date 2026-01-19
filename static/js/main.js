const video = document.getElementById('video');
const verifyBtn = document.getElementById('verify');
const result = document.getElementById('result');

async function initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'}});
    video.srcObject = stream;
  } catch (e) {
    showResult('Cannot access camera: ' + e.message, false);
  }
}

function captureDataUrl() {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.9);
}

function showResult(msg, ok) {
  result.classList.remove('d-none','alert-danger','alert-success');
  result.classList.add(ok ? 'alert-success' : 'alert-danger');
  result.textContent = msg;
}

verifyBtn?.addEventListener('click', async ()=>{
  showResult('Verifying...', true);
  const dataUrl = captureDataUrl();
  try {
    const resp = await fetch('/api/verify', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({image: dataUrl})});
    const j = await resp.json();
    if (j.error) showResult('Error: ' + j.error, false);
    else if (j.match) showResult('Hello, ' + j.name + '! Attendance recorded.', true);
    else showResult('Face not recognized.', false);
  } catch (e) {
    showResult('Request failed: ' + e.message, false);
  }
});

initCamera();
