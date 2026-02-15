/**
 * form.js — Login form: validation, password toggle, scroll-fade observer
 */

(function () {
    'use strict';

    // -- form validation with custom messages --
    var form = document.getElementById('credentials-form');
    if (form) {
        form.addEventListener('submit', function () {
            var emailInput = document.getElementById('vt_email');
            var passwordInput = document.getElementById('vt_password');

            emailInput.setCustomValidity(
                emailInput.value ? '' : 'Please enter your Virginia Tech email address.'
            );
            passwordInput.setCustomValidity(
                passwordInput.value ? '' : 'Please enter your password.'
            );
        });
    }

    // reset custom message as the user types
    document.querySelectorAll('input').forEach(function (input) {
        input.addEventListener('input', function () {
            this.setCustomValidity('');
        });
    });

    // -- password visibility toggle --
    var toggleBtn = document.getElementById('toggle-password');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            var pw = document.getElementById('vt_password');
            var eyeOpen = document.getElementById('eye-icon');
            var eyeSlash = document.getElementById('eye-slash-icon');
            var isHidden = pw.type === 'password';

            pw.type = isHidden ? 'text' : 'password';
            eyeOpen.style.display = isHidden ? 'none' : '';
            eyeSlash.style.display = isHidden ? '' : 'none';
            this.title = isHidden ? 'Hide password' : 'Show password';
            pw.focus();
        });
    }

    // -- fade-in on scroll (IntersectionObserver) --
    var observer = new IntersectionObserver(
        function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        },
        { threshold: 0.15 }
    );

    document.querySelectorAll('.fade-in').forEach(function (el) {
        observer.observe(el);
    });
})();
