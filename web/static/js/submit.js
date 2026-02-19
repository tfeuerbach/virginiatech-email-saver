/**
 * submit.js — Progress polling and animation state machine for the submit page
 */

import { animationSteps, animationUrls } from '/static/js/animationConfig.js';
import { initializeAnimation, updateAnimationVisibility } from '/static/js/animationUtils.js';

// boot up each lottie canvas
Object.entries(animationUrls).forEach(function ([step, url]) {
    initializeAnimation(animationSteps[step], url);
});

var lastStep = 1;

var stepMessages = {
    1: 'Storing your credentials securely...',
    2: 'Attempting to log in...',
    3: 'Sending a push notification to your device...',
    4: 'Login Successful! Redirecting to your dashboard...',
    5: 'Something went wrong. Redirecting...',
};

function updateProgress(step, errorMsg) {
    if (step === lastStep) return;
    lastStep = step;

    updateAnimationVisibility(step, animationSteps);

    var statusMessage = document.getElementById('status-message');
    if (step === 5 && errorMsg) {
        statusMessage.textContent = errorMsg;
    } else {
        statusMessage.textContent = stepMessages[step] || 'Processing...';
    }

    if (step === 4) {
        setTimeout(function () { window.location.href = '/dashboard'; }, 1000);
    } else if (step === 5) {
        setTimeout(function () { window.location.href = '/'; }, 3000);
    }
}

function pollProgress() {
    fetch('/get_progress')
        .then(function (res) { return res.json(); })
        .then(function (data) { updateProgress(data.step, data.error); })
        .catch(function (err) { console.error('Error polling progress:', err); });
}

setInterval(pollProgress, 1000);
