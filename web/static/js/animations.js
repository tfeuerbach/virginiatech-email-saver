import { DotLottie } from "https://esm.sh/@lottiefiles/dotlottie-web";

// Animation container and form container
const animationContainer = document.getElementById("animation-container");
const formContainer = document.getElementById("form-container");

// Map animations to their canvas elements
const animationSteps = {
    1: "storing-animation",
    2: "login-animation",
    3: "push-animation",
    4: "success-animation",
};

// Store initialized animations
const initializedAnimations = {};

// Helper: Initialize DotLottie animation
function initializeAnimation(canvasId, src) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas with ID ${canvasId} not found.`);
        return;
    }

    // Set canvas dimensions explicitly
    canvas.width = 300;
    canvas.height = 300;

    try {
        initializedAnimations[canvasId] = new DotLottie({
            canvas,
            src,
            loop: true,
            autoplay: true,
        });
        console.log(`Initialized animation for ${canvasId}`);
    } catch (error) {
        console.error(`Failed to initialize animation for ${canvasId}:`, error);
    }
}

// Show a specific animation based on step
function showProgressStep(step) {
    if (!animationContainer) {
        console.error("Animation container not found.");
        return;
    }

    animationContainer.classList.remove("hidden");

    // Hide all animations
    Object.values(animationSteps).forEach((id) => {
        const canvas = document.getElementById(id);
        if (canvas) {
            canvas.style.visibility = "hidden";
            canvas.style.opacity = "0";
        }
    });

    // Show the current animation
    const canvasId = animationSteps[step];
    const currentCanvas = document.getElementById(canvasId);

    if (currentCanvas) {
        currentCanvas.style.visibility = "visible";
        currentCanvas.style.opacity = "1";

        // Initialize the animation if not already initialized
        if (!initializedAnimations[canvasId]) {
            const animationUrls = {
                1: "https://lottie.host/8ac3bb2a-cbac-4f01-b1ed-8f9f850500f8/pkUIu7XE1d.json",
                2: "https://lottie.host/431a01f1-1cdd-4a9c-8a6d-bb87f44cdde0/uSDs8Ocycr.lottie",
                3: "https://lottie.host/8a9d29dc-29d9-4640-902d-279f4e6e7065/5EivasZcWd.lottie",
                4: "https://lottie.host/588ea9d1-e0c7-4fca-91e9-360ea89bcc10/AzcUHnoUuK.lottie",
            };
            initializeAnimation(canvasId, animationUrls[step]);
        } else {
            try {
                initializedAnimations[canvasId].play();
            } catch (error) {
                console.error(`Failed to play animation for step ${step}:`, error);
            }
        }
    }

    // Hide the form container at step 1
    if (step === 1 && formContainer) {
        formContainer.classList.add("hidden");
    }
}

// Handle form submission
const form = document.getElementById("credentials-form");
if (form) {
    form.addEventListener("submit", function (e) {
        e.preventDefault(); // Prevent default form submission behavior

        const email = document.getElementById("vt_email").value;
        const username = email.split("@")[0]; // Extract username from email
        const password = document.getElementById("vt_password").value;

        // Save email in local storage to use in the processing page
        localStorage.setItem("email", email);

        // Redirect to the processing page
        window.location.href = "/processing";

        // Send form data to the backend asynchronously
        fetch("/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                vt_email: email,
                vt_username: username,
                vt_password: password,
            }),
        }).catch((error) => {
            console.error("Error during form submission:", error);
        });
    });
}

// Poll the server for progress updates
function pollProgress() {
    if (!animationContainer) return; // Ensure polling doesn't run without animations

    fetch("/get_progress")
        .then((response) => response.json())
        .then((data) => {
            const step = data.step;
            showProgressStep(step); // Update animations based on progress
        })
        .catch((error) => console.error("Error polling progress:", error));
}

// Start polling every second if on a page with animations
if (animationContainer) {
    setInterval(pollProgress, 1000);
}

// Export for global usage
window.showProgressStep = showProgressStep;
