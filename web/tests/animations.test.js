/**
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import { updateAnimationVisibility } from '../static/js/animationUtils.js';

describe('updateAnimationVisibility', () => {
    it('should show the correct animation and hide others', () => {
        document.body.innerHTML = `
            <canvas id="storing-animation" class="animation hidden"></canvas>
            <canvas id="login-animation" class="animation hidden"></canvas>
        `;

        const animationSteps = {
            1: 'storing-animation',
            2: 'login-animation',
        };

        updateAnimationVisibility(1, animationSteps);

        expect(document.getElementById('storing-animation').classList).toContain('visible');
        expect(document.getElementById('login-animation').classList).toContain('hidden');
    });

    it('should handle non-existent animation IDs gracefully', () => {
        document.body.innerHTML = `
            <canvas id="storing-animation" class="animation hidden"></canvas>
        `;

        const animationSteps = {
            1: 'non-existent-animation',
        };

        updateAnimationVisibility(1, animationSteps);

        expect(document.getElementById('storing-animation').classList).toContain('hidden');
    });
});
