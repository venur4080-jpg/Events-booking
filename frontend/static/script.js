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
    if (!window.__ebCaptchaPageshowBound) {
        window.__ebCaptchaPageshowBound = true;
        window.addEventListener('pageshow', () => {
            document.querySelectorAll('[data-captcha-group]').forEach((group) => {
                group.querySelectorAll('.captcha-digit-box').forEach((box) => {
                    box.disabled = false;
                    box.removeAttribute('aria-disabled');
                });
                syncCaptchaDigitGroup(group);
            });
        });
    }

    const groups = document.querySelectorAll('[data-captcha-group]');
    groups.forEach((group) => {
        if (group.dataset.captchaBound === '1') return;
        group.dataset.captchaBound = '1';

        const boxes = Array.from(group.querySelectorAll('.captcha-digit-box'));
        const form = group.closest('form');
        if (form && form.dataset.captchaSubmitBound !== '1') {
            form.dataset.captchaSubmitBound = '1';
            form.addEventListener('submit', (e) => {
                form.querySelectorAll('[data-captcha-group]').forEach(syncCaptchaDigitGroup);
                if (e.defaultPrevented) return;
                if (typeof form.checkValidity === 'function' && !form.checkValidity()) return;
                // Disable display-only digit boxes on submit so only the hidden
                // captcha value submits and browser autofill (e.g. Edge Wallet /
                // "Save driver's license") never offers to save CAPTCHA digits.
                form.querySelectorAll('[data-captcha-group] .captcha-digit-box').forEach((box) => {
                    box.disabled = true;
                    box.setAttribute('aria-disabled', 'true');
                });
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

// =========================================================================
// PLAIN-TEXT EVENT NAME COPY + GLOBAL PUBLIC SHARE MODAL
// =========================================================================
function copyEventPlainText(text, label = 'Copied') {
    const clean = String(text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return Promise.resolve(false);

    const notify = () => {
        if (typeof window.showToast === 'function') {
            window.showToast(`${label} copied!`, 'success');
        }
        return true;
    };

    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        return navigator.clipboard.writeText(clean).then(notify).catch(() => _fallbackPlainCopy(clean, notify));
    }
    return Promise.resolve(_fallbackPlainCopy(clean, notify));
}

function _fallbackPlainCopy(clean, notify) {
    try {
        const ta = document.createElement('textarea');
        ta.value = clean;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        return notify();
    } catch (_) {
        return false;
    }
}

function _initEventTitlePlainCopyAndClick() {
    if (window.__eventCopyHandlersBound) return;
    window.__eventCopyHandlersBound = true;

    const titleSelector = '.event-copy-title, .details-hero-title, .highlight-card-title, .grid-event-card-title, .event-title';

    document.addEventListener('copy', (e) => {
        const sel = window.getSelection ? window.getSelection() : null;
        if (!sel || sel.isCollapsed || !e.clipboardData) return;
        const anchorEl = sel.anchorNode ? (sel.anchorNode.nodeType === 3 ? sel.anchorNode.parentElement : sel.anchorNode) : null;
        const focusEl = sel.focusNode ? (sel.focusNode.nodeType === 3 ? sel.focusNode.parentElement : sel.focusNode) : null;
        const matchedTitle = (anchorEl && anchorEl.closest && anchorEl.closest(titleSelector))
            || (focusEl && focusEl.closest && focusEl.closest(titleSelector));
        if (!matchedTitle) return;

        const plain = sel.toString().replace(/\s*\n+\s*/g, ' ').trim();
        if (!plain) return;
        e.preventDefault();
        e.clipboardData.setData('text/plain', plain);
    });

    document.addEventListener('click', (e) => {
        const copyTitleEl = e.target && e.target.closest ? e.target.closest('.event-copy-title[data-event-url]') : null;
        if (!copyTitleEl) return;
        if (e.target.closest('a, button')) return;
        const sel = window.getSelection ? window.getSelection() : null;
        if (sel && sel.toString().trim().length > 0) return;
        const url = copyTitleEl.getAttribute('data-event-url');
        if (url) window.location.href = url;
    });

    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        const copyTitleEl = e.target && e.target.closest ? e.target.closest('.event-copy-title[data-event-url]') : null;
        if (!copyTitleEl) return;
        e.preventDefault();
        const url = copyTitleEl.getAttribute('data-event-url');
        if (url) window.location.href = url;
    });
}

function _ensureShareEventModal() {
    let overlay = document.getElementById('globalShareEventModal');
    if (overlay) return overlay;

    overlay = document.createElement('div');
    overlay.id = 'globalShareEventModal';
    overlay.className = 'share-event-modal-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'shareModalEventTitle');
    overlay.innerHTML = `
        <div class="share-event-modal-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:0.65rem;">
                <div>
                    <div id="shareModalMeta" style="font-size:0.75rem;color:#38bdf8;font-weight:700;text-transform:uppercase;letter-spacing:0.7px;margin-bottom:4px;">Public Event Link</div>
                    <h3 id="shareModalEventTitle" class="event-copy-title" style="margin:0;font-size:1.22rem;font-weight:800;line-height:1.3;"></h3>
                </div>
                <button type="button" id="shareModalCloseBtn" aria-label="Close share dialog" style="background:none;border:none;color:#94a3b8;font-size:1.5rem;line-height:1;cursor:pointer;">&times;</button>
            </div>
            <p style="font-size:0.82rem;color:#94a3b8;margin:0;line-height:1.45;">
                Anyone with this public link can inspect event details. Logging in is required before registering.
            </p>
            <div class="share-link-row">
                <input type="text" id="shareModalUrlInput" class="share-link-input" readonly aria-label="Public event link">
                <button type="button" id="shareModalCopyLinkBtn" class="btn-primary" style="width:auto;margin:0;padding:0.62rem 1rem;border-radius:10px;font-size:0.82rem;white-space:nowrap;">🔗 Copy Link</button>
            </div>
            <div class="share-channels-grid">
                <button type="button" id="shareModalCopyNameBtn" class="share-channel-pill">📋 Copy Event Name Only</button>
                <a id="shareModalWhatsapp" class="share-channel-pill" target="_blank" rel="noopener noreferrer" style="color:#25d366;border-color:rgba(37,211,102,0.35);">💬 WhatsApp</a>
                <a id="shareModalTwitter" class="share-channel-pill" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;border-color:rgba(56,189,248,0.35);">𝕏 Share</a>
                <a id="shareModalLinkedin" class="share-channel-pill" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;border-color:rgba(96,165,250,0.35);">💼 LinkedIn</a>
                <button type="button" id="shareModalNativeBtn" class="share-channel-pill" style="display:none;">📤 Device Share</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeShareEventModal();
    });
    document.getElementById('shareModalCloseBtn').addEventListener('click', closeShareEventModal);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && overlay.classList.contains('active')) closeShareEventModal();
    });
    return overlay;
}

function openShareEventModal(options) {
    const opts = options || {};
    const title = String(opts.title || 'Event').trim();
    const rawUrl = String(opts.url || window.location.href).trim();
    let absUrl = rawUrl;
    try {
        absUrl = new URL(rawUrl, window.location.origin).href;
    } catch (_) {
        absUrl = window.location.href;
    }

    const overlay = _ensureShareEventModal();
    const titleEl = document.getElementById('shareModalEventTitle');
    const metaEl = document.getElementById('shareModalMeta');
    const urlInput = document.getElementById('shareModalUrlInput');
    const copyLinkBtn = document.getElementById('shareModalCopyLinkBtn');
    const copyNameBtn = document.getElementById('shareModalCopyNameBtn');
    const waLink = document.getElementById('shareModalWhatsapp');
    const xLink = document.getElementById('shareModalTwitter');
    const liLink = document.getElementById('shareModalLinkedin');
    const nativeBtn = document.getElementById('shareModalNativeBtn');

    if (titleEl) titleEl.textContent = title;
    const metaParts = [opts.category, opts.date].filter(Boolean);
    if (metaEl) metaEl.textContent = metaParts.length ? `Public Link • ${metaParts.join(' • ')}` : 'Public Event Link';
    if (urlInput) {
        urlInput.value = absUrl;
        urlInput.onclick = () => urlInput.select();
    }

    if (copyLinkBtn) {
        copyLinkBtn.onclick = () => copyEventPlainText(absUrl, 'Public event link');
    }
    if (copyNameBtn) {
        copyNameBtn.onclick = () => copyEventPlainText(title, 'Event name');
    }
    if (waLink) {
        waLink.href = `https://wa.me/?text=${encodeURIComponent(title + ' ' + absUrl)}`;
    }
    if (xLink) {
        xLink.href = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(absUrl)}`;
    }
    if (liLink) {
        liLink.href = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(absUrl)}`;
    }
    if (nativeBtn) {
        if (typeof navigator.share === 'function') {
            nativeBtn.style.display = 'inline-flex';
            nativeBtn.onclick = () => navigator.share({ title, text: title, url: absUrl }).catch(() => {});
        } else {
            nativeBtn.style.display = 'none';
        }
    }

    overlay.classList.add('active');
}

function closeShareEventModal() {
    const overlay = document.getElementById('globalShareEventModal');
    if (overlay) overlay.classList.remove('active');
}

function shareEventFromBtn(btn, evt) {
    if (evt) {
        evt.preventDefault();
        evt.stopPropagation();
    }
    if (!btn) return;
    openShareEventModal({
        title: btn.getAttribute('data-share-title') || '',
        url: btn.getAttribute('data-share-url') || window.location.href,
        category: btn.getAttribute('data-share-category') || '',
        date: btn.getAttribute('data-share-date') || '',
    });
}

document.addEventListener('DOMContentLoaded', _initEventTitlePlainCopyAndClick);

