// dashboard.js

(function () {
    'use strict';

    var isSample = document.querySelector('.dash[data-sample-mode="true"]');
    if (isSample) {
        // Public sample for TFV reviewers — display only, no API calls.
        return;
    }

    var csrf = document.querySelector('meta[name="csrf-token"]').content;

    function formatDateTime(utcDateTime) {
        var d = new Date(utcDateTime);
        return d.toLocaleString(undefined, {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZoneName: 'short',
        });
    }

    function postJson(url, body) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify(body),
        });
    }

    // localize timestamps
    ['last-login', 'next-login', 'scheduler-next-check', 'scheduler-last-check']
        .forEach(function (id) {
            var el = document.getElementById(id);
            if (el && el.dataset.time) {
                el.textContent = formatDateTime(el.dataset.time);
            }
        });

    // cadence slider
    (function () {
        var slider = document.getElementById('cadence-slider');
        var valueLabel = document.getElementById('cadence-value');
        var saveBtn = document.getElementById('save-cadence-btn');
        var statusEl = document.getElementById('cadence-status');
        var nextLoginEl = document.getElementById('next-login');
        var savedValue = parseInt(slider.dataset.savedCadence, 10);

        slider.addEventListener('input', function () {
            valueLabel.textContent = this.value;
            saveBtn.disabled = (parseInt(this.value, 10) === savedValue);
        });

        saveBtn.addEventListener('click', function () {
            var newCadence = parseInt(slider.value, 10);
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
            statusEl.textContent = '';

            postJson('/update_cadence', { login_cadence_days: newCadence })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.error) {
                        statusEl.textContent = data.error;
                        statusEl.style.color = '#ff6b6b';
                        saveBtn.disabled = false;
                    } else {
                        statusEl.textContent = data.message;
                        statusEl.style.color = '#90ee90';
                        saveBtn.textContent = 'Save';
                        savedValue = newCadence;
                        if (data.next_login && nextLoginEl) {
                            nextLoginEl.textContent = formatDateTime(data.next_login);
                        }
                    }
                })
                .catch(function () {
                    statusEl.textContent = 'Failed to save. Please try again.';
                    statusEl.style.color = '#ff6b6b';
                    saveBtn.disabled = false;
                    saveBtn.textContent = 'Save';
                });
        });
    })();

    // timezone (overview bar)
    (function () {
        var displayText = document.getElementById('tz-display-text');
        var changeBtn = document.getElementById('tz-change-btn');
        var editPanel = document.getElementById('tz-edit');
        var tzSelect = document.getElementById('tz-select');
        var saveBtn = document.getElementById('tz-save-btn');
        var cancelBtn = document.getElementById('tz-cancel-btn');
        var displayWrap = document.getElementById('tz-display');
        var nextLoginEl = document.getElementById('next-login');

        if (!displayText || !tzSelect) return;

        var tzNames = {
            'America/New_York': 'Eastern', 'America/Chicago': 'Central',
            'America/Denver': 'Mountain', 'America/Los_Angeles': 'Pacific',
            'America/Anchorage': 'Alaska', 'Pacific/Honolulu': 'Hawaii',
            'UTC': 'UTC',
        };

        function friendlyTz(iana) {
            return tzNames[iana] || iana;
        }

        // auto-detect if not stored
        var browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
        if (!displayText.textContent.trim() && browserTz) {
            displayText.textContent = friendlyTz(browserTz);
            if (tzSelect.querySelector('option[value="' + browserTz + '"]')) {
                tzSelect.value = browserTz;
            }
            postJson('/update_timezone', { timezone: browserTz });
        }

        changeBtn.addEventListener('click', function () {
            displayWrap.style.display = 'none';
            editPanel.style.display = '';
        });

        cancelBtn.addEventListener('click', function () {
            editPanel.style.display = 'none';
            displayWrap.style.display = '';
        });

        saveBtn.addEventListener('click', function () {
            saveBtn.disabled = true;
            saveBtn.textContent = '...';

            postJson('/update_timezone', { timezone: tzSelect.value })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    saveBtn.disabled = false;
                    saveBtn.textContent = 'Save';
                    if (data.error) return;
                    displayText.textContent = data.timezone_label;
                    editPanel.style.display = 'none';
                    displayWrap.style.display = '';
                    if (data.next_login && nextLoginEl) {
                        nextLoginEl.textContent = data.next_login;
                    }
                })
                .catch(function () {
                    saveBtn.disabled = false;
                    saveBtn.textContent = 'Save';
                });
        });
    })();

    // preferred login time
    (function () {
        var hourSelect = document.getElementById('preferred-hour');
        var noPrefOption = document.getElementById('no-pref-option');
        var saveBtn = document.getElementById('save-preferred-btn');
        var statusEl = document.getElementById('preferred-status');
        var nextLoginEl = document.getElementById('next-login');

        if (!hourSelect) return;

        // show local time on "no preference" option
        if (noPrefOption && nextLoginEl && nextLoginEl.dataset.time) {
            try {
                var d = new Date(nextLoginEl.dataset.time);
                if (!isNaN(d.getTime())) {
                    var localTime = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
                    noPrefOption.textContent = 'No preference (currently ' + localTime + ')';
                }
            } catch (e) { /* leave default text */ }
        }

        var savedHour = hourSelect.value;

        hourSelect.addEventListener('change', function () {
            saveBtn.disabled = (hourSelect.value === savedHour);
        });

        saveBtn.addEventListener('click', function () {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
            statusEl.textContent = '';

            var hour = hourSelect.value === '' ? null : parseInt(hourSelect.value, 10);

            postJson('/update_preferred_time', { preferred_hour: hour })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    saveBtn.textContent = 'Save';
                    if (data.error) {
                        statusEl.textContent = data.error;
                        statusEl.style.color = '#ff6b6b';
                        saveBtn.disabled = false;
                    } else {
                        statusEl.textContent = data.message;
                        statusEl.style.color = '#90ee90';
                        savedHour = hourSelect.value;
                        if (data.next_login && nextLoginEl) {
                            nextLoginEl.textContent = data.next_login;
                        }
                    }
                })
                .catch(function () {
                    statusEl.textContent = 'Failed to save. Please try again.';
                    statusEl.style.color = '#ff6b6b';
                    saveBtn.disabled = false;
                    saveBtn.textContent = 'Save';
                });
        });
    })();

    // email opt-in toggle
    (function () {
        var toggle = document.getElementById('email-opt-in-toggle');
        if (!toggle) return;
        var panel = document.getElementById('email-settings-panel');

        toggle.addEventListener('change', function () {
            var optIn = toggle.checked;
            if (panel) panel.style.display = optIn ? '' : 'none';

            postJson('/update_email_opt_in', { email_opt_in: optIn })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.error) {
                        toggle.checked = !optIn;
                        if (panel) panel.style.display = !optIn ? '' : 'none';
                    }
                })
                .catch(function () {
                    toggle.checked = !optIn;
                    if (panel) panel.style.display = !optIn ? '' : 'none';
                });
        });
    })();

    // notification email editing
    (function () {
        var display = document.getElementById('notif-email-display');
        var input = document.getElementById('notif-email-input');
        var editBtn = document.getElementById('notif-email-edit');
        var saveBtn = document.getElementById('notif-email-save');
        var cancelBtn = document.getElementById('notif-email-cancel');
        var statusEl = document.getElementById('notif-email-status');

        function showEdit() {
            display.style.display = 'none';
            editBtn.style.display = 'none';
            input.style.display = '';
            saveBtn.style.display = '';
            cancelBtn.style.display = '';
            input.focus();
            statusEl.textContent = '';
        }

        function showDisplay(email) {
            if (email) display.textContent = email;
            display.style.display = '';
            editBtn.style.display = '';
            input.style.display = 'none';
            saveBtn.style.display = 'none';
            cancelBtn.style.display = 'none';
        }

        editBtn.addEventListener('click', showEdit);

        cancelBtn.addEventListener('click', function () {
            input.value = display.textContent;
            showDisplay();
        });

        saveBtn.addEventListener('click', function () {
            saveBtn.textContent = '...';
            statusEl.textContent = '';

            postJson('/update_notification_email', { notification_email: input.value })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    saveBtn.textContent = 'Save';
                    if (data.error) {
                        statusEl.textContent = data.error;
                        statusEl.style.color = '#ff6b6b';
                    } else {
                        statusEl.textContent = data.message;
                        statusEl.style.color = '#90ee90';
                        showDisplay(data.notification_email);
                        input.value = data.notification_email;
                    }
                })
                .catch(function () {
                    statusEl.textContent = 'Failed to save.';
                    statusEl.style.color = '#ff6b6b';
                    saveBtn.textContent = 'Save';
                });
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); saveBtn.click(); }
            if (e.key === 'Escape') cancelBtn.click();
        });
    })();

    // privacy-policy modal
    (function () {
        var modal = document.getElementById('privacy-modal');
        var openBtns = document.querySelectorAll('#open-privacy-modal, #footer-privacy-link');
        var closeBtn = document.getElementById('close-privacy-modal');
        if (!modal || !openBtns.length) return;

        function open() {
            modal.style.display = '';
            document.body.style.overflow = 'hidden';
        }
        function close() {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }

        openBtns.forEach(function (btn) {
            btn.addEventListener('click', function (e) { e.preventDefault(); open(); });
        });
        closeBtn.addEventListener('click', close);
        modal.addEventListener('click', function (e) { if (e.target === modal) close(); });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && modal.style.display !== 'none') close();
        });
    })();

    // SMS opt-in
    (function () {
        var toggle = document.getElementById('sms-opt-in-toggle');
        var panel = document.getElementById('sms-opt-in-panel');
        var phoneInput = document.getElementById('sms-phone-input');
        var consentCheckbox = document.getElementById('sms-consent-checkbox');
        var saveBtn = document.getElementById('sms-save-btn');
        var statusEl = document.getElementById('sms-status');

        function updateSaveState() {
            if (!saveBtn || !consentCheckbox || !phoneInput) return;
            var phoneReady = phoneInput.value.replace(/\D/g, '').length >= 10;
            saveBtn.disabled = !(consentCheckbox.checked && phoneReady);
        }

        toggle.addEventListener('change', function () {
            if (this.checked) {
                panel.style.display = '';
                phoneInput.focus();
                updateSaveState();
            } else {
                saveSms(false, '', false);
            }
        });

        consentCheckbox.addEventListener('change', updateSaveState);
        phoneInput.addEventListener('input', updateSaveState);

        saveBtn.addEventListener('click', function () {
            if (!consentCheckbox.checked) {
                statusEl.textContent = 'Please check the SMS consent box to continue.';
                statusEl.style.color = '#ff6b6b';
                return;
            }
            saveSms(true, phoneInput.value, true);
        });

        phoneInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); saveBtn.click(); }
        });

        updateSaveState();

        function saveSms(optIn, phone, consent) {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
            statusEl.textContent = '';

            postJson('/update_sms_preferences', {
                sms_opt_in: optIn,
                phone_number: phone,
                sms_consent: consent,
            })
                .then(function (res) {
                    return res.json().then(function (d) { return { ok: res.ok, data: d }; });
                })
                .then(function (result) {
                    saveBtn.textContent = 'Save';
                    if (!result.ok) {
                        statusEl.textContent = result.data.error || 'Something went wrong';
                        statusEl.style.color = '#ff6b6b';
                        toggle.checked = true;
                        panel.style.display = '';
                        updateSaveState();
                        return;
                    }
                    statusEl.textContent = result.data.message;
                    statusEl.style.color = '#90ee90';
                    if (result.data.sms_opt_in) {
                        phoneInput.value = result.data.phone_number;
                        consentCheckbox.checked = true;
                    } else {
                        toggle.checked = false;
                        panel.style.display = 'none';
                        phoneInput.value = '';
                        consentCheckbox.checked = false;
                    }
                    updateSaveState();
                })
                .catch(function () {
                    saveBtn.textContent = 'Save';
                    statusEl.textContent = 'Failed to save. Please try again.';
                    statusEl.style.color = '#ff6b6b';
                    updateSaveState();
                });
        }
    })();

    // account removal (swipe to reveal, then confirm)
    (function () {
        var track = document.getElementById('swipe-track');
        var thumb = document.getElementById('swipe-thumb');
        var fill = document.getElementById('swipe-fill');
        var confirmPanel = document.getElementById('delete-confirm');
        var confirmYes = document.getElementById('delete-confirm-yes');
        var confirmCancel = document.getElementById('delete-confirm-cancel');

        var dragging = false;
        var startX = 0;
        var thumbW = 0;
        var trackW = 0;
        var maxX = 0;
        var completed = false;

        function getX(e) {
            return e.touches ? e.touches[0].clientX : e.clientX;
        }

        function begin(e) {
            if (completed) return;
            dragging = true;
            startX = getX(e) - thumb.offsetLeft;
            thumbW = thumb.offsetWidth;
            trackW = track.offsetWidth;
            maxX = trackW - thumbW;
            thumb.style.transition = 'none';
            fill.style.transition = 'none';
            e.preventDefault();
        }

        function move(e) {
            if (!dragging) return;
            var x = Math.min(Math.max(0, getX(e) - startX), maxX);
            thumb.style.left = x + 'px';
            fill.style.width = (x + thumbW) + 'px';
            e.preventDefault();
        }

        function end() {
            if (!dragging) return;
            dragging = false;
            thumb.style.transition = '';
            fill.style.transition = '';

            var current = thumb.offsetLeft;
            if (current >= maxX * 0.85) {
                completed = true;
                thumb.style.left = maxX + 'px';
                fill.style.width = trackW + 'px';
                track.classList.add('swipe-complete');
                setTimeout(function () {
                    track.style.display = 'none';
                    confirmPanel.style.display = '';
                }, 300);
            } else {
                thumb.style.left = '0px';
                fill.style.width = thumbW + 'px';
            }
        }

        thumb.addEventListener('mousedown', begin);
        thumb.addEventListener('touchstart', begin, { passive: false });
        window.addEventListener('mousemove', move);
        window.addEventListener('touchmove', move, { passive: false });
        window.addEventListener('mouseup', end);
        window.addEventListener('touchend', end);

        confirmCancel.addEventListener('click', function () {
            confirmPanel.style.display = 'none';
            track.style.display = '';
            track.classList.remove('swipe-complete');
            completed = false;
            thumb.style.left = '0px';
            fill.style.width = thumb.offsetWidth + 'px';
        });

        confirmYes.addEventListener('click', function () {
            confirmYes.disabled = true;
            confirmYes.textContent = 'Removing...';

            postJson('/delete_account', {})
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.redirect) window.location.href = data.redirect;
                })
                .catch(function () {
                    confirmYes.disabled = false;
                    confirmYes.textContent = 'Yes, remove my account';
                });
        });
    })();

})();
