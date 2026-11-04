/**
 * frontend/static/subscription_popup.js
 * Professionally designed Subscription Interstitial Popup Modal.
 * Triggers on:
 *   1. New user registration.
 *   2. Login without active subscription.
 *   3. Accessing premium features without subscription (e.g. 1080p/2K video, multi-camera, VIP chat crown).
 *   4. Expired subscription reminder.
 * 
 * Features:
 *   - Monthly & Annual toggle with savings calculation.
 *   - Feature matrix breakdown.
 *   - Anti-annoyance cooldown (suppresses automatic display for 24 hours upon "Maybe Later").
 *   - Direct interactive trigger support via window.triggerSubscriptionGate(featureName).
 */

(function () {
    const COOLDOWN_HOURS = 24;
    const DISMISS_KEY = 'sub_popup_dismissed_at';

    function isCooldownActive() {
        const dismissedAt = localStorage.getItem(DISMISS_KEY);
        if (!dismissedAt) return false;
        const elapsedHours = (Date.now() - parseInt(dismissedAt, 10)) / (1000 * 60 * 60);
        return elapsedHours < COOLDOWN_HOURS;
    }

    function dismissPopup() {
        localStorage.setItem(DISMISS_KEY, Date.now().toString());
        const modal = document.getElementById('globalSubPopupModal');
        if (modal) modal.style.display = 'none';
    }

    function injectPopupDOM() {
        if (document.getElementById('globalSubPopupModal')) return;

        const modalDiv = document.createElement('div');
        modalDiv.id = 'globalSubPopupModal';
        modalDiv.style.cssText = `
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(4, 5, 10, 0.88);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            z-index: 999999;
            align-items: center;
            justify-content: center;
            padding: 1.2rem;
            box-sizing: border-box;
            animation: subFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        `;

        modalDiv.innerHTML = `
            <style>
                @keyframes subFadeIn {
                    from { opacity: 0; transform: scale(0.96); }
                    to { opacity: 1; transform: scale(1); }
                }
                .sub-pop-card {
                    background: linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(13, 13, 20, 0.98) 100%);
                    border: 1.5px solid rgba(0, 139, 227, 0.4);
                    border-radius: 24px;
                    max-width: 680px;
                    width: 100%;
                    padding: 2.2rem;
                    box-shadow: 0 25px 70px rgba(0, 0, 0, 0.9), 0 0 30px rgba(0, 139, 227, 0.2);
                    box-sizing: border-box;
                    color: #ffffff;
                    font-family: 'Inter', -apple-system, sans-serif;
                    position: relative;
                    max-height: 92vh;
                    overflow-y: auto;
                }
                .sub-pop-header {
                    text-align: center;
                    margin-bottom: 1.5rem;
                }
                .sub-pop-title {
                    font-family: 'Outfit', sans-serif;
                    font-size: 1.9rem;
                    font-weight: 900;
                    margin: 0 0 6px;
                    background: linear-gradient(135deg, #ffffff 0%, #38bdf8 60%, #ff5eb0 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .sub-pop-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 1.2rem;
                    margin: 1.5rem 0;
                }
                @media (max-width: 600px) {
                    .sub-pop-grid { grid-template-columns: 1fr; }
                    .sub-pop-card { padding: 1.5rem; }
                }
                .sub-pop-tile {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 18px;
                    padding: 1.4rem 1.2rem;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    transition: all 0.2s;
                }
                .sub-pop-tile.featured {
                    border-color: #ff1389;
                    background: linear-gradient(180deg, rgba(255, 19, 137, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%);
                    box-shadow: 0 0 25px rgba(255, 19, 137, 0.2);
                }
            </style>
            <div class="sub-pop-card">
                <button type="button" onclick="window.dismissSubscriptionPopup()" style="position: absolute; top: 1.2rem; right: 1.4rem; background: none; border: none; color: #94a3b8; font-size: 1.6rem; cursor: pointer;">✕</button>
                
                <div class="sub-pop-header">
                    <span id="subPopupBadge" style="background: rgba(0, 139, 227, 0.15); border: 1px solid rgba(0, 139, 227, 0.4); color: #008be3; font-size: 0.76rem; font-weight: 800; padding: 4px 12px; border-radius: 20px; text-transform: uppercase;">
                        👑 VIP Stage Streaming
                    </span>
                    <h2 class="sub-pop-title" id="subPopupHeading">Unlock Unlimited Live Events</h2>
                    <p id="subPopupSubtitle" style="color: #94a3b8; font-size: 0.92rem; margin: 0; line-height: 1.5;">
                        Watch all live summits, multi-camera angle feeds, and interactive stage Q&A without paying per-event pass fees.
                    </p>

                    </div>

                <!-- Plans Comparison -->
                <div class="sub-pop-grid">
                    <!-- Normal Pack -->
                    <div class="sub-pop-tile">
                        <div>
                            <div style="font-size: 1.4rem; margin-bottom: 4px;">💎 Normal Pack</div>
                            <div style="color: #94a3b8; font-size: 0.78rem; margin-bottom: 12px;">720p HD live broadcast pass</div>
                            <div style="margin-bottom: 12px;">
                                <span style="font-size: 1.2rem; font-weight: 800; color: #008be3;">₹</span>
                                <span id="popNormalPrice" style="font-family: 'Outfit', sans-serif; font-size: 2rem; font-weight: 900; color: #ffffff;">899</span>
                                <span id="popNormalCycle" style="font-size: 0.8rem; color: #94a3b8;">/ year</span>
                            </div>
                            <ul style="list-style: none; padding: 0; margin: 0 0 1rem; font-size: 0.82rem; color: #cbd5e1; display: flex; flex-direction: column; gap: 6px;">
                                <li>✓ 1 User / Device screen</li>
                                <li>✓ 720p HD Quality stream</li>
                                <li>✓ FREE access to events &le; ₹1,000</li>
                                <li>✓ Zero commercial interruptions</li>
                            </ul>
                        </div>
                        <a href="/subscriptions" style="background: rgba(0, 139, 227, 0.15); border: 1px solid rgba(0, 139, 227, 0.4); color: #008be3; text-decoration: none; text-align: center; padding: 10px; border-radius: 50px; font-weight: 800; font-size: 0.82rem; display: block; text-transform: uppercase;">
                            Select Normal
                        </a>
                    </div>

                    <!-- Super Pack VIP -->
                    <div class="sub-pop-tile featured">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <div style="font-size: 1.4rem; font-weight: 800; color: #ffffff;">👑 Super VIP</div>
                                <span style="background: #ff1389; color: #fff; font-size: 0.65rem; font-weight: 800; padding: 2px 8px; border-radius: 20px; text-transform: uppercase;">Recommended</span>
                            </div>
                            <div style="color: #ff5eb0; font-size: 0.78rem; margin-bottom: 12px;">Ultra 2K QHD & all events free</div>
                            <div style="margin-bottom: 12px;">
                                <span style="font-size: 1.2rem; font-weight: 800; color: #ff1389;">₹</span>
                                <span id="popSuperPrice" style="font-family: 'Outfit', sans-serif; font-size: 2rem; font-weight: 900; color: #ffffff;">1,499</span>
                                <span id="popSuperCycle" style="font-size: 0.8rem; color: #94a3b8;">/ year</span>
                            </div>
                            <ul style="list-style: none; padding: 0; margin: 0 0 1rem; font-size: 0.82rem; color: #cbd5e1; display: flex; flex-direction: column; gap: 6px;">
                                <li>✓ 2 Screens simultaneously</li>
                                <li>✓ 1080p FHD & 2K QHD Ultra</li>
                                <li>✓ <strong>ALL Events Free (Even > ₹1,000!)</strong></li>
                                <li>✓ 👑 VIP Crown Badge in Live Chat</li>
                                <li>✓ Multi-Camera Backstage Feed</li>
                            </ul>
                        </div>
                        <a href="/subscriptions" style="background: linear-gradient(135deg, #ff1389 0%, #008be3 100%); color: #ffffff; text-decoration: none; text-align: center; padding: 10px; border-radius: 50px; font-weight: 800; font-size: 0.82rem; display: block; text-transform: uppercase; box-shadow: 0 4px 15px rgba(255, 19, 137, 0.4);">
                            Get Super VIP ➔
                        </a>
                    </div>
                </div>

                <!-- Footer Dismiss -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 14px; margin-top: 10px;">
                    <button type="button" onclick="window.dismissSubscriptionPopup()" style="background: none; border: none; color: #94a3b8; font-size: 0.84rem; cursor: pointer; text-decoration: underline;">
                        Maybe Later (Don't show again today)
                    </button>
                    <a href="/subscriptions" style="color: #38bdf8; font-size: 0.84rem; font-weight: 700; text-decoration: none;">
                        View Full Comparison Matrix →
                    </a>
                </div>
            </div>
        `;

        document.body.appendChild(modalDiv);
    }

    let popupCycle = 'yearly';
    window.setPopupCycle = function (cycle) {
        popupCycle = cycle;
        const bM = document.getElementById('popBtnMonthly');
        const bY = document.getElementById('popBtnYearly');
        if (bM && bY) {
            bM.style.background = cycle === 'monthly' ? 'linear-gradient(135deg, #008be3, #0062a3)' : 'transparent';
            bM.style.color = cycle === 'monthly' ? '#ffffff' : '#94a3b8';
            bY.style.background = cycle === 'yearly' ? 'linear-gradient(135deg, #008be3, #0062a3)' : 'transparent';
            bY.style.color = cycle === 'yearly' ? '#ffffff' : '#94a3b8';
        }

        if (cycle === 'yearly') {
            document.getElementById('popNormalPrice').textContent = '899';
            document.getElementById('popNormalCycle').textContent = '/ year';
            document.getElementById('popSuperPrice').textContent = '1,499';
            document.getElementById('popSuperCycle').textContent = '/ year';
        } else {
            document.getElementById('popNormalPrice').textContent = '149';
            document.getElementById('popNormalCycle').textContent = '/ month';
            document.getElementById('popSuperPrice').textContent = '299';
            document.getElementById('popSuperCycle').textContent = '/ month';
        }
    };

    window.dismissSubscriptionPopup = function () {
        dismissPopup();
    };

    window.showSubscriptionModal = function (context) {
        injectPopupDOM();
        const modal = document.getElementById('globalSubPopupModal');
        const titleEl = document.getElementById('subPopupHeading');
        const subEl = document.getElementById('subPopupSubtitle');
        const badgeEl = document.getElementById('subPopupBadge');

        if (context === 'register') {
            badgeEl.textContent = '🎉 New Member Welcome Gift';
            titleEl.textContent = 'Welcome! Enjoy 50% Off VIP Streaming';
            subEl.textContent = 'Subscribe today to stream unlimited tech workshops and college hackathons in crystal-clear HD.';
        } else if (context === 'expired') {
            badgeEl.textContent = '⚠️ Subscription Expired';
            titleEl.textContent = 'Your VIP Access has Expired';
            subEl.textContent = 'Renew your subscription pack to regain ad-free 1080p live broadcasts and free event registrations.';
        } else if (context === 'feature_gate') {
            badgeEl.textContent = '🔒 Premium Feature Locked';
            titleEl.textContent = 'Upgrade to Super Pack VIP';
            subEl.textContent = '1080p FHD, 2K QHD, multi-camera stage angles, and VIP Chat Crowns are exclusive to Super Pack subscribers.';
        } else if (context === 'in_grace_period') {
            badgeEl.textContent = '⏳ Grace Period Ending Soon';
            titleEl.textContent = 'Keep Your VIP Stream Benefits';
            subEl.textContent = 'Your subscription is in a 3-day grace period. Renew now to avoid interruption.';
        }

        modal.style.display = 'flex';
    };

    window.triggerSubscriptionGate = function (featureName) {
        window.showSubscriptionModal('feature_gate');
    };

    // Auto-check on page load
    async function checkAutoPopup() {
        // Do not auto popup on subscription page itself
        if (window.location.pathname.startsWith('/subscriptions') || window.location.pathname.startsWith('/admin')) {
            return;
        }

        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('registered') === '1' || urlParams.get('welcome') === '1') {
            window.showSubscriptionModal('register');
            return;
        }

        // If cooldown active, skip automatic popups
        if (isCooldownActive()) {
            return;
        }

        try {
            const res = await fetch('/api/subscription/popup-status');
            const data = await res.json();
            if (data.ok && data.trigger && data.trigger !== 'none') {
                if (data.trigger === 'expired') {
                    window.showSubscriptionModal('expired');
                } else if (data.trigger === 'in_grace_period') {
                    window.showSubscriptionModal('in_grace_period');
                } else if (data.trigger === 'login_unsubscribed') {
                    window.showSubscriptionModal('login_unsubscribed');
                }
            }
        } catch (e) {
            // Silently ignore if offline
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', checkAutoPopup);
    } else {
        setTimeout(checkAutoPopup, 1000);
    }
})();

