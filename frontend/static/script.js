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
});
