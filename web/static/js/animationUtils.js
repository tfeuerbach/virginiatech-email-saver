const DOTLOTTIE_VERSION = "0.63.0";
const DOTLOTTIE_CDN = `https://esm.sh/@lottiefiles/dotlottie-web@${DOTLOTTIE_VERSION}`;
const DOTLOTTIE_WASM = `https://cdn.jsdelivr.net/npm/@lottiefiles/dotlottie-web@${DOTLOTTIE_VERSION}/dist/dotlottie-player.wasm`;

let DotLottie;
async function loadDotLottie() {
  if (!DotLottie) {
    try {
      if (typeof window !== "undefined") {
        const mod = await import(DOTLOTTIE_CDN);
        if (mod.setWasmUrl) {
          mod.setWasmUrl(DOTLOTTIE_WASM);
        }
        DotLottie = mod.DotLottie;
      } else {
        DotLottie = require("@lottiefiles/dotlottie-web").DotLottie;
      }
    } catch (error) {
      console.error("Error loading DotLottie:", error);
    }
  }
  return DotLottie;
}

const initializedAnimations = {};

export async function initializeAnimation(canvasId, src) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) {
    console.error(`Canvas with ID ${canvasId} not found.`);
    return;
  }

  canvas.width = 300;
  canvas.height = 300;

  try {
    const DotLottie = await loadDotLottie();
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
  Object.values(animationSteps).forEach((id) => {
    const canvas = document.getElementById(id);
    if (canvas) {
      canvas.classList.add("hidden");
      canvas.classList.remove("visible");
    }
  });

  const currentCanvasId = animationSteps[step];
  const currentCanvas = document.getElementById(currentCanvasId);
  if (currentCanvas) {
    currentCanvas.classList.add("visible");
    currentCanvas.classList.remove("hidden");
  }
}
