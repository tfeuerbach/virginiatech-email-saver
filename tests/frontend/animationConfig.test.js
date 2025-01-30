import { describe, it, expect } from 'vitest';
import { animationSteps, animationUrls } from '../../web/static/js/animationConfig.js';

describe('animationConfig', () => {
    it('should map steps to correct canvas IDs', () => {
        expect(animationSteps[1]).toBe('storing-animation');
        expect(animationSteps[2]).toBe('login-animation');
        expect(animationSteps[3]).toBe('push-animation');
        expect(animationSteps[4]).toBe('success-animation');
        expect(animationSteps[5]).toBe('error-animation'); // Include error animation
    });

    it('should contain valid Lottie URLs', () => {
        Object.values(animationUrls).forEach((url) => {
            expect(url).toMatch(/^https:\/\/lottie\.host/);
        });
    });

    it('should have consistent keys between steps and URLs', () => {
        const stepsKeys = Object.keys(animationSteps);
        const urlsKeys = Object.keys(animationUrls);

        expect(stepsKeys).toEqual(urlsKeys);
    });
});
