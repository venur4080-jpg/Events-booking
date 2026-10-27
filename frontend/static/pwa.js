/**
 * pwa.js - Progressive Web App Client Controller & Offline Ticket Wallet Assistant
 */
(function() {
  'use strict';

  // 1. Register Service Worker
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js')
        .then((reg) => {
          console.log('[PWA] Service Worker active with scope:', reg.scope);
        })
        .catch((err) => {
          console.warn('[PWA] Service Worker registration failed:', err);
        });
    });
  }

  // 2. Offline / Online Connectivity Monitors
  function updateNetworkStatus() {
    const isOnline = navigator.onLine;
    let statusBadge = document.getElementById('pwa-network-badge');
    
    if (!isOnline) {
      if (!statusBadge) {
        statusBadge = document.createElement('div');
        statusBadge.id = 'pwa-network-badge';
        statusBadge.style.cssText = `
          position: fixed;
          bottom: 20px;
          left: 50%;
          transform: translateX(-50%);
          background: linear-gradient(135deg, #ef4444, #dc2626);
          color: #ffffff;
          padding: 8px 18px;
          border-radius: 50px;
          font-size: 0.85rem;
          font-weight: 700;
          box-shadow: 0 10px 25px rgba(239, 68, 68, 0.4);
          z-index: 999999;
          display: flex;
          align-items: center;
          gap: 8px;
          animation: slideUp 0.3s ease;
        `;
        statusBadge.innerHTML = `<span>📴 Offline Mode</span> <span style="font-size:0.75rem;opacity:0.9;">• Cached Passes Available</span>`;
        document.body.appendChild(statusBadge);
      }
    } else {
      if (statusBadge) {
        statusBadge.style.background = 'linear-gradient(135deg, #10b981, #059669)';
        statusBadge.innerHTML = `<span>🟢 Back Online</span>`;
        setTimeout(() => {
          if (statusBadge && statusBadge.parentNode) {
            statusBadge.parentNode.removeChild(statusBadge);
          }
        }, 3000);
      }
    }
  }

  window.addEventListener('online', updateNetworkStatus);
  window.addEventListener('offline', updateNetworkStatus);

  // 3. PWA Installation Prompt Manager
  let deferredPrompt = null;

  window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the mini-infobar from appearing on mobile
    e.preventDefault();
    deferredPrompt = e;
    
    // Check if user previously dismissed install prompt
    if (localStorage.getItem('pwa_install_dismissed') === 'true') {
      return;
    }

    // Show custom installation banner after 3 seconds
    setTimeout(showInstallBanner, 3000);
  });

  function showInstallBanner() {
    if (!deferredPrompt || document.getElementById('pwa-install-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'pwa-install-banner';
    banner.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      max-width: 360px;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid rgba(0, 242, 254, 0.4);
      border-radius: 16px;
      padding: 16px 20px;
      box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5), 0 0 20px rgba(0, 242, 254, 0.15);
      backdrop-filter: blur(16px);
      z-index: 999998;
      display: flex;
      flex-direction: column;
      gap: 10px;
      animation: fadeIn 0.4s ease;
      font-family: inherit;
    `;

    banner.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:10px;">
          <img src="/static/logo.png" alt="Events Booking Logo" style="width:32px;height:32px;border-radius:8px;object-fit:cover;">
          <div>
            <div style="font-weight:800;color:#ffffff;font-size:0.95rem;">Install Events Booking App</div>
            <div style="color:#94a3b8;font-size:0.75rem;">Fast access & offline ticket wallet</div>
          </div>
        </div>
        <button id="pwa-close-btn" style="background:none;border:none;color:#94a3b8;font-size:1.2rem;cursor:pointer;line-height:1;">&times;</button>
      </div>
      <div style="display:flex;gap:8px;margin-top:4px;">
        <button id="pwa-install-btn" style="flex:1;background:var(--primary, #008be3);color:#070709;border:none;padding:8px 12px;border-radius:8px;font-weight:700;font-size:0.85rem;cursor:pointer;transition:transform 0.2s;box-shadow: 0 4px 12px rgba(0,139,227,0.35);">
          📲 Install Now
        </button>
        <button id="pwa-later-btn" style="background:rgba(255,255,255,0.06);color:#e2e8f0;border:1px solid rgba(255,255,255,0.1);padding:8px 12px;border-radius:8px;font-weight:600;font-size:0.85rem;cursor:pointer;">
          Maybe Later
        </button>
      </div>
    `;

    document.body.appendChild(banner);

    const installBtn = banner.querySelector('#pwa-install-btn');
    const laterBtn = banner.querySelector('#pwa-later-btn');
    const closeBtn = banner.querySelector('#pwa-close-btn');

    if (installBtn) {
      installBtn.addEventListener('click', async () => {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        console.log('[PWA] User response to install:', outcome);
        deferredPrompt = null;
        banner.remove();
      });
    }

    const dismissBanner = () => {
      localStorage.setItem('pwa_install_dismissed', 'true');
      banner.remove();
    };

    if (laterBtn) laterBtn.addEventListener('click', dismissBanner);
    if (closeBtn) closeBtn.addEventListener('click', dismissBanner);
  }

  window.addEventListener('appinstalled', () => {
    console.log('[PWA] App successfully installed!');
    const banner = document.getElementById('pwa-install-banner');
    if (banner) banner.remove();
  });
})();
