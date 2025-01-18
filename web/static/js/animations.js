// animations.js

// Animation container and form container
const animationContainer = document.getElementById("animation-container");
const formContainer = document.getElementById("form-container");

// Animation steps mapped to their container IDs
const animationSteps = {
    1: "storing-credentials",
    2: "attempting-login",
    3: "push-notification",
    4: "success",
};

// Show a specific animation based on step
function showProgressStep(step) {
    // Ensure animation container is visible
    animationContainer.classList.remove("hidden");

    // Hide all animation steps first
    Object.values(animationSteps).forEach((id) => {
        const element = document.getElementById(id);
        if (element) {
            element.classList.add("hidden");
        }
    });

    // Show the current animation step
    const currentAnimation = document.getElementById(animationSteps[step]);
    if (currentAnimation) {
        currentAnimation.classList.remove("hidden");
    }

    // If the step is 1, hide the form container
    if (step === 1) {
        formContainer.classList.add("hidden");
    }
}

// Export for usage in HTML
window.showProgressStep = showProgressStep;