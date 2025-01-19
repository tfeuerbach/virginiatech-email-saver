// animations.js

// Animation container and form container
const animationContainer = document.getElementById("animation-container");
const formContainer = document.getElementById("form-container");

// Animation steps mapped to container IDs
const animationSteps = {
    1: "storing-credentials",
    2: "attempting-login",
    3: "push-notification",
    4: "success",
};

// Show a specific animation based on step
function showProgressStep(step) {
    animationContainer.classList.remove("hidden"); // Ensure the container is visible

    // Hide all animation steps
    Object.values(animationSteps).forEach((id) => {
        const element = document.getElementById(id);
        if (element) element.classList.add("hidden");
    });

    // Show the selected animation step
    const currentAnimation = document.getElementById(animationSteps[step]);
    if (currentAnimation) currentAnimation.classList.remove("hidden");

    // Hide the form container when starting animations
    if (step === 1) formContainer.classList.add("hidden");
}

// Export for usage in HTML
window.showProgressStep = showProgressStep;