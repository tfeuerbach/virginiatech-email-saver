/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { initializeAnimation } from '../static/js/animationUtils.js';
import { DotLottie } from '@lottiefiles/dotlottie-web';

// Mock DotLottie and its methods
vi.mock('@lottiefiles/dotlottie-web', () => ({
    DotLottie: vi.fn().mockImplementation(() => ({
        play: vi.fn(),
    })),
}));

// Mock localStorage at the global level
Object.defineProperty(global, 'localStorage', {
    value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
    },
    writable: true,
});

describe('initializeAnimation', () => {
    it('should initialize a Lottie animation correctly', () => {
        // Prepare DOM
        document.body.innerHTML = '<canvas id="test-animation"></canvas>';

        // Call initializeAnimation
        initializeAnimation('test-animation', 'https://lottie.host/example-animation.json');

        // Assert canvas properties
        const canvas = document.getElementById('test-animation');
        expect(canvas.width).toBe(300);
        expect(canvas.height).toBe(300);

        // Ensure DotLottie is initialized correctly
        expect(DotLottie).toHaveBeenCalledWith({
            canvas,
            src: 'https://lottie.host/example-animation.json',
            loop: true,
            autoplay: true,
        });
    });

    it('should log an error if canvas is not found', () => {
        // Spy on console.error
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

        // Call initializeAnimation with a non-existent canvas
        initializeAnimation('non-existent-canvas', 'https://lottie.host/example-animation.json');

        // Verify error logging
        expect(consoleSpy).toHaveBeenCalledWith('Canvas with ID non-existent-canvas not found.');

        // Restore console
        consoleSpy.mockRestore();
    });

    it('should handle initialization errors gracefully', () => {
        // Prepare DOM
        document.body.innerHTML = '<canvas id="test-animation"></canvas>';

        // Simulate DotLottie throwing an error
        DotLottie.mockImplementationOnce(() => {
            throw new Error('Initialization error');
        });

        // Spy on console.error
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

        // Call initializeAnimation
        initializeAnimation('test-animation', 'https://lottie.host/example-animation.json');

        // Verify error logging
        expect(consoleSpy).toHaveBeenCalledWith(
            'Failed to initialize animation for test-animation:',
            expect.any(Error)
        );

        // Restore console
        consoleSpy.mockRestore();
    });
});
