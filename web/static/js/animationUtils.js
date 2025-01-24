import { DotLottie } from "https://esm.sh/@lottiefiles/dotlottie-web";

const initializedAnimations = {};

export function initializeAnimation(canvasId, src) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas with ID ${canvasId} not found.`);
        return;
    }

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

export function updateAnimationVisibility(step, animationSteps) {
    // Hide all animations
    Object.values(animationSteps).forEach((id) => {
        const canvas = document.getElementById(id);
        if (canvas) {
            canvas.classList.add("hidden");
            canvas.classList.remove("visible");
        }
    });

    // Show the current animation
    const currentCanvasId = animationSteps[step];
    const currentCanvas = document.getElementById(currentCanvasId);
    if (currentCanvas) {
        currentCanvas.classList.add("visible");
        currentCanvas.classList.remove("hidden");
    }
}
