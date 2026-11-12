/* 
 * Events Booking - Client Side Logic & Validation Suite
 */

function registerEvent(eventName) {
    alert(`Successfully registered for ${eventName}! We will send details to your email.`);
}

/**
 * Universal Mobile Number Validator
 * Rules:
 * - Exactly 10 digits
 * - Only numeric digits (no letters, alphabets, or special characters)
 * - Starts with standard mobile prefix (6, 7, 8, or 9)
 */
function validateMobileNumber(phone) {
    if (!phone || typeof phone !== 'string' || !phone.trim()) {
        return { valid: false, error: 'Mobile number is required.' };
    }
    let raw = phone.trim();
    
    // Check for alphabets or non-phone characters explicitly first
    if (/[a-zA-Z]/.test(raw)) {
        return { valid: false, error: 'Mobile number must contain digits only (letters/alphabets are not allowed).' };
    }

    // Strip leading +91 or 0
    let cleaned = raw.replace(/^\+91[\s-]*/, '');
    if (cleaned.length === 11 && cleaned.startsWith('0')) {
        cleaned = cleaned.substring(1);
    }
    cleaned = cleaned.replace(/[\s-]/g, '');

    if (!/^\d+$/.test(cleaned)) {
        return { valid: false, error: 'Mobile number must contain numeric digits only.' };
    }
    if (cleaned.length !== 10) {
        return { valid: false, error: `Mobile number must be exactly 10 digits (you entered ${cleaned.length} digits).` };
    }
    if (!/^[6-9]\d{9}$/.test(cleaned)) {
        return { valid: false, error: 'Mobile number must start with 6, 7, 8, or 9 (standard 10-digit mobile).' };
    }
    return { valid: true, cleaned: cleaned };
}

/**
 * Universal Email Validator
 * Rules:
 * - Valid RFC-compliant email structure: username@domain.tld
 * - Detects typos and missing letters (e.g. venur4080@gmail.co missing 'm' in .com)
 * - TLD minimum length >= 2 letters
 */
function validateEmailAddress(email) {
    if (!email || typeof email !== 'string' || !email.trim()) {
        return { valid: false, error: 'Email address is required.' };
    }
    let val = email.trim().toLowerCase();

    // General pattern check
    const emailPattern = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$/;
    if (!emailPattern.test(val) || val.includes('..') || val.startsWith('.') || val.includes('@.')) {
        return { valid: false, error: 'Invalid email format (e.g. username@example.com).' };
    }

    const parts = val.split('@');
    if (parts.length !== 2) {
        return { valid: false, error: 'Invalid email address.' };
    }
    const domain = parts[1];

    // Typo detection for popular email providers
    const gmailTypos = ['gmail.co', 'gmail.con', 'gmail.cm', 'gmail.cpm', 'gmai.com', 'gamil.com', 'gmal.com', 'gemail.com', 'gmail.om'];
    if (gmailTypos.includes(domain)) {
        return { valid: false, error: "Invalid email: Did you mean '@gmail.com'? (Missing 'm' in .co or domain misspelled)." };
    }

    const yahooTypos = ['yahoo.co', 'yahoo.con', 'yahoo.cm', 'yaho.com', 'yahho.com'];
    if (yahooTypos.includes(domain)) {
        return { valid: false, error: "Invalid email: Did you mean '@yahoo.com' or '@yahoo.co.in'?" };
    }

    const msTypos = ['outlook.co', 'outlook.con', 'outlok.com', 'hotmail.co', 'hotmail.con', 'hotmial.com'];
    if (msTypos.includes(domain)) {
        return { valid: false, error: "Invalid email: Did you mean '@outlook.com' or '@hotmail.com'?" };
    }

    const icloudTypos = ['icloud.co', 'icloud.con', 'icoud.com'];
    if (icloudTypos.includes(domain)) {
        return { valid: false, error: "Invalid email: Did you mean '@icloud.com'?" };
    }

    const domainParts = domain.split('.');
    const tld = domainParts[domainParts.length - 1];
    if (tld.length < 2) {
        return { valid: false, error: `Invalid top-level domain '.${tld}' in email address.` };
    }

    return { valid: true, cleaned: val };
}

// Automatic same-origin CSRF header attachment for fetch() calls
(function () {
    const origFetch = window.fetch;
    if (!origFetch) return;
    window.fetch = function (input, init) {
        const opts = init ? Object.assign({}, init) : {};
        const method = (opts.method || 'GET').toUpperCase();
        if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
            const url = typeof input === 'string' ? input : (input && input.url) || '';
            const sameOrigin = !url || url.startsWith('/') || url.startsWith(window.location.origin);
            if (sameOrigin) {
                const meta = document.querySelector('meta[name="csrf-token"]');
                const token = meta ? meta.getAttribute('content') : '';
                if (token) {
                    const hdrs = new Headers(opts.headers || {});
                    if (!hdrs.has('X-CSRF-Token')) {
                        hdrs.set('X-CSRF-Token', token);
                    }
                    opts.headers = hdrs;
                }
            }
        }
        return origFetch.call(this, input, opts);
    };
})();

// Prevent background scroll leak when scrolling over sidebar
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.addEventListener('wheel', function(e) {
            e.stopPropagation();
            const atTop = e.deltaY < 0 && sidebar.scrollTop <= 0;
            const atBottom = e.deltaY > 0 && (sidebar.scrollTop + sidebar.clientHeight >= sidebar.scrollHeight - 1);
            if (atTop || atBottom) {
                e.preventDefault();
            }
        }, { passive: false });
    }
    initCaptchaDigitGroups();
});

/**
 * Bind 5-box OTP-style numeric CAPTCHA inputs to a backing hidden form field.
 * Supports single-digit typing with auto-advance, multi-digit paste,
 * Backspace navigation, and Left/Right arrow navigation.
 */
function syncCaptchaDigitGroup(group) {
    if (!group) return '';
    const hiddenId = group.getAttribute('data-captcha-group');
    const hiddenEl = hiddenId ? document.getElementById(hiddenId) : null;
    const boxes = Array.from(group.querySelectorAll('.captcha-digit-box'));
    const combined = boxes.map((b) => {
        const clean = (b.value || '').replace(/\D/g, '').slice(0, 1);
        if (b.value !== clean) b.value = clean;
        b.classList.toggle('is-filled', clean.length === 1);
        return clean;
    }).join('');
    if (hiddenEl) hiddenEl.value = combined;
    return combined;
}

function clearCaptchaDigitGroup(hiddenId) {
    const group = document.querySelector(`[data-captcha-group="${hiddenId}"]`);
    const hiddenEl = document.getElementById(hiddenId);
    if (hiddenEl) hiddenEl.value = '';
    if (!group) return;
    const boxes = Array.from(group.querySelectorAll('.captcha-digit-box'));
    boxes.forEach((b) => {
        b.value = '';
        b.classList.remove('is-filled');
    });
    if (boxes[0]) boxes[0].focus();
}

function initCaptchaDigitGroups() {
    const groups = document.querySelectorAll('[data-captcha-group]');
    groups.forEach((group) => {
        if (group.dataset.captchaBound === '1') return;
        group.dataset.captchaBound = '1';

        const boxes = Array.from(group.querySelectorAll('.captcha-digit-box'));
        const form = group.closest('form');
        if (form && form.dataset.captchaSubmitBound !== '1') {
            form.dataset.captchaSubmitBound = '1';
            form.addEventListener('submit', () => {
                form.querySelectorAll('[data-captcha-group]').forEach(syncCaptchaDigitGroup);
            });
        }

        const fillFromIndex = (startIdx, digits) => {
            if (!digits) {
                syncCaptchaDigitGroup(group);
                return;
            }
            let pos = startIdx;
            for (const ch of digits) {
                if (pos >= boxes.length) break;
                boxes[pos].value = ch;
                pos += 1;
            }
            syncCaptchaDigitGroup(group);
            const focusIdx = Math.min(pos, boxes.length - 1);
            if (boxes[focusIdx]) boxes[focusIdx].focus();
        };

        boxes.forEach((box, idx) => {
            box.addEventListener('focus', () => {
                setTimeout(() => box.select(), 0);
            });

            box.addEventListener('input', () => {
                const digits = (box.value || '').replace(/\D/g, '');
                if (digits.length > 1) {
                    fillFromIndex(idx, digits);
                    return;
                }
                box.value = digits;
                syncCaptchaDigitGroup(group);
                if (digits.length === 1 && idx < boxes.length - 1) {
                    boxes[idx + 1].focus();
                }
            });

            box.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace') {
                    if (!box.value && idx > 0) {
                        e.preventDefault();
                        boxes[idx - 1].value = '';
                        syncCaptchaDigitGroup(group);
                        boxes[idx - 1].focus();
                    } else {
                        setTimeout(() => syncCaptchaDigitGroup(group), 0);
                    }
                } else if (e.key === 'ArrowLeft' && idx > 0) {
                    e.preventDefault();
                    boxes[idx - 1].focus();
                } else if (e.key === 'ArrowRight' && idx < boxes.length - 1) {
                    e.preventDefault();
                    boxes[idx + 1].focus();
                }
            });

            box.addEventListener('paste', (e) => {
                const raw = (e.clipboardData || window.clipboardData)?.getData('text') || '';
                const digits = raw.replace(/\D/g, '');
                if (!digits) return;
                e.preventDefault();
                const start = digits.length >= boxes.length ? 0 : idx;
                fillFromIndex(start, digits);
            });
        });

        syncCaptchaDigitGroup(group);
    });
}
