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

/**
 * Universal Sidebar Drawer & Background Scroll-Lock Engine
 * - Guarantees isolated sidebar scrolling without moving background page
 * - Auto-creates backdrop blur overlay
 * - MutationObserver syncs with individual page script toggles
 * - Consumes wheel events to prevent scroll chaining
 */
(function() {
    function initSidebarEngine() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        // Auto-inject overlay if not present
        let overlay = document.getElementById('sidebarOverlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'sidebarOverlay';
            overlay.className = 'sidebar-overlay';
            overlay.setAttribute('aria-hidden', 'true');
            document.body.appendChild(overlay);
        }

        function openSidebar() {
            sidebar.classList.add('active');
            sidebar.setAttribute('aria-hidden', 'false');
            document.body.classList.add('sidebar-open');
            if (overlay) overlay.classList.add('active');
            const hamburger = document.getElementById('hamburger');
            if (hamburger) hamburger.setAttribute('aria-expanded', 'true');
        }

        function closeSidebar() {
            sidebar.classList.remove('active');
            sidebar.setAttribute('aria-hidden', 'true');
            document.body.classList.remove('sidebar-open');
            if (overlay) overlay.classList.remove('active');
            const hamburger = document.getElementById('hamburger');
            if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
        }

        // Click delegation
        document.addEventListener('click', function(e) {
            const hamburger = e.target.closest('#hamburger');
            if (hamburger) {
                e.preventDefault();
                e.stopPropagation();
                if (sidebar.classList.contains('active')) {
                    closeSidebar();
                } else {
                    openSidebar();
                }
                return;
            }

            const closeBtn = e.target.closest('#closeSidebar, .close-btn');
            if (closeBtn && sidebar.contains(closeBtn)) {
                e.preventDefault();
                e.stopPropagation();
                closeSidebar();
                return;
            }

            if (e.target === overlay) {
                e.preventDefault();
                e.stopPropagation();
                closeSidebar();
                return;
            }

            // Outside click when open
            if (sidebar.classList.contains('active') && !sidebar.contains(e.target)) {
                closeSidebar();
            }
        }, true);

        // Escape key to close
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && sidebar.classList.contains('active')) {
                closeSidebar();
            }
        });

        // Strict Wheel Scroll Isolation: guarantees wheel events never leak to background body
        sidebar.addEventListener('wheel', function(e) {
            e.stopPropagation();
            const scrollTop = sidebar.scrollTop;
            const scrollHeight = sidebar.scrollHeight;
            const height = sidebar.clientHeight;
            const delta = e.deltaY;

            // At boundaries, consume wheel so background page won't scroll
            if ((delta < 0 && scrollTop <= 0) || (delta > 0 && (scrollTop + height >= scrollHeight - 1))) {
                e.preventDefault();
            }
        }, { passive: false });

        // Touchmove containment for mobile
        if (overlay) {
            overlay.addEventListener('touchmove', function(e) {
                e.preventDefault();
            }, { passive: false });
        }

        // MutationObserver to sync with any legacy page-level hamburger click handlers
        const observer = new MutationObserver(function(mutations) {
            for (let i = 0; i < mutations.length; i++) {
                if (mutations[i].attributeName === 'class') {
                    const isActive = sidebar.classList.contains('active');
                    if (isActive) {
                        document.body.classList.add('sidebar-open');
                        if (overlay) overlay.classList.add('active');
                    } else {
                        document.body.classList.remove('sidebar-open');
                        if (overlay) overlay.classList.remove('active');
                    }
                    break;
                }
            }
        });
        observer.observe(sidebar, { attributes: true, attributeFilter: ['class'] });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSidebarEngine);
    } else {
        initSidebarEngine();
    }
})();
