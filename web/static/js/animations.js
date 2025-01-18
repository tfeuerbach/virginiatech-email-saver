// animations.js

// Animation elements
const animations = {
    storing: document.getElementById('storing-animation'),
    login: document.getElementById('login-animation'),
    push: document.getElementById('push-animation'),
    success: document.getElementById('success-animation'),
};

// Animation container and form container
const animationContainer = document.getElementById('animation-container');
const formContainer = document.getElementById('form-container');

// Start an animation by key
function startAnimation(key) {
    Object.keys(animations).forEach(k => {
        if (k === key) {
            animations[k].style.display = 'block'; // Show the current animation
        } else {
            animations[k].style.display = 'none'; // Hide others
        }
    });
}

// Show progress and manage animations
function showProgressStep(step) {
    if (step === 1) {
        animationContainer.classList.remove('hidden'); // Show the animation container
        formContainer.classList.add('hidden'); // Hide the form container
    }
    switch (step) {
        case 1:
            startAnimation('storing');
            break;
        case 2:
            startAnimation('login');
            break;
        case 3:
            startAnimation('push');
            break;
        case 4:
            startAnimation('success');
            break;
        default:
            console.error('Invalid step');
    }
}

// Handle form submission
const form = document.getElementById('credentials-form');
form.addEventListener('submit', (event) => {
    event.preventDefault(); // Prevent the default form submission
    showProgressStep(1); // Start with the storing animation

    // Simulate API call and animation progression
    setTimeout(() => showProgressStep(2), 2000); // Login animation
    setTimeout(() => showProgressStep(3), 4000); // Push notification animation
    setTimeout(() => showProgressStep(4), 6000); // Success animation

    // Redirect or perform additional logic after success
    setTimeout(() => {
        window.location.href = '/dashboard'; // Redirect to dashboard
    }, 8000);
});

// Export for usage in HTML
window.showProgressStep = showProgressStep;