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

    // -- scroll-linked slide-up for How It Works section --
    var howSection = document.getElementById('how-it-works');
    var scrollHint = document.querySelector('.scroll-hint');
    var issueLink = document.querySelector('.issue-link');
    if (howSection) {
        var mainContainer = document.getElementById('main-container');
        var cardGlass = document.querySelector('.card-glass');
        var cardBottomDoc = cardGlass
            ? cardGlass.getBoundingClientRect().bottom + window.pageYOffset
            : 0;
        var mainHeight = mainContainer ? mainContainer.offsetHeight : window.innerHeight;
        var maxPull = Math.max(mainHeight - cardBottomDoc - 246, 0);

        // lock the page height so margin changes can't cause scroll jiggle
        document.body.style.minHeight = document.documentElement.scrollHeight + 'px';

        var ticking = false;

        window.addEventListener('scroll', function () {
            if (!ticking) {
                requestAnimationFrame(function () {
                    var scrollY = window.pageYOffset;
                    var pull = Math.min(scrollY * 0.8, maxPull);
                    howSection.style.marginTop = (-pull) + 'px';

                    // fade out scroll hint + issue link as user scrolls
                    var fade = Math.max(1 - scrollY / 120, 0);
                    if (scrollHint) {
                        scrollHint.style.opacity = fade;
                        scrollHint.style.pointerEvents = fade < 0.1 ? 'none' : '';
                    }
                    if (issueLink) {
                        issueLink.style.opacity = fade;
                    }
                    ticking = false;
                });
                ticking = true;
            }
        }, { passive: true });
    }
})();
