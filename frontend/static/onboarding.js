/**
 * onboarding.js – First-login walkthrough modal for Events Booking
 */

const ONBOARDING_KEY = 'events_onboarding_done_v1';

const slides = [
  {
    icon: '🏠',
    title: 'Welcome to Events Booking!',
    body: 'Your all-in-one platform for discovering and booking hackathons, workshops & seminars. Let us give you a quick tour!'
  },
  {
    icon: '🔍',
    title: 'Discover & Filter Events',
    body: 'Use the search bar and filters to find events by category (AI & ML, Web Dev, Gaming…) or price (Free / Paid).'
  },
  {
    icon: '📅',
    title: 'Calendar View',
    body: 'Switch to Calendar View to see all events laid out by date – colour-coded by type, just like Google Calendar.'
  },
  {
    icon: '🎟️',
    title: 'Register & Download Tickets',
    body: 'Click Register on any upcoming event. After registering you can download your PDF ticket instantly.'
  },
  {
    icon: '⚙️',
    title: 'Personalise Your Experience',
    body: 'Customise your aesthetics, high-definition Nature Wallpapers, theme colours, and Dark / Light mode anytime in Settings.'
  },
  {
    icon: '✅',
    title: "You're all set!",
    body: "Explore EVENTS and enjoy the experience. Click Finish to get started – you won't see this tour again."
  }
];

let currentSlide = 0;

function buildOnboardingModal() {
  const overlay = document.createElement('div');
  overlay.id = 'onboardingOverlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-labelledby', 'ob-title');
  overlay.style.cssText = `
    position: fixed; inset: 0; z-index: 99999;
    display: flex; align-items: center; justify-content: center;
    background: rgba(0,0,0,0.65); backdrop-filter: blur(6px);
    opacity: 0; transition: opacity 0.4s ease;
  `;

  overlay.innerHTML = `
    <div id="onboardingModal" style="
      background: var(--bg-card, #1e293b);
      border: 1px solid var(--glass-border, rgba(255,255,255,0.12));
      border-radius: 24px;
      box-shadow: 0 32px 80px rgba(0,0,0,0.6);
      max-width: 480px; width: 90%;
      padding: 0;
      overflow: hidden;
      transform: translateY(30px) scale(0.97);
      transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.4s ease;
      opacity: 0;
    ">
      <!-- Progress Bar -->
      <div style="height: 4px; background: rgba(255,255,255,0.08);">
        <div id="ob-progress" style="height:100%; background: var(--primary, #00f2fe); width:0%; transition: width 0.4s ease; border-radius: 4px;"></div>
      </div>

      <!-- Content Area -->
      <div style="padding: 2.5rem 2.5rem 1.5rem; text-align: center;">
        <div id="ob-icon" style="font-size: 4rem; margin-bottom: 1rem; line-height: 1; transition: opacity 0.3s ease;"></div>
        <h2 id="ob-title" style="font-size: 1.6rem; font-weight: 800; color: var(--text-main, #f1f5f9); margin-bottom: 0.75rem; transition: opacity 0.3s ease;"></h2>
        <p id="ob-body" style="color: var(--text-muted, #94a3b8); line-height: 1.7; font-size: 1rem; transition: opacity 0.3s ease;"></p>
      </div>

      <!-- Step Dots -->
      <div id="ob-dots" style="display: flex; justify-content: center; gap: 8px; padding-bottom: 1.5rem;"></div>

      <!-- Buttons -->
      <div style="
        display: flex; justify-content: space-between; align-items: center;
        padding: 1.25rem 2rem;
        border-top: 1px solid var(--glass-border, rgba(255,255,255,0.08));
        gap: 1rem;
      ">
        <button id="ob-skip" onclick="closeOnboarding()" style="
          background: transparent; border: 1px solid var(--glass-border, rgba(255,255,255,0.15));
          color: var(--text-muted, #94a3b8); padding: 0.6rem 1.2rem;
          border-radius: 50px; cursor: pointer; font-size: 0.9rem;
          transition: all 0.2s ease; font-family: inherit;
        " aria-label="Skip tour">Skip Tour</button>

        <div style="display: flex; gap: 0.75rem;">
          <button id="ob-prev" onclick="onboardPrev()" style="
            background: rgba(255,255,255,0.08); border: 1px solid var(--glass-border, rgba(255,255,255,0.15));
            color: var(--text-main, #f1f5f9); padding: 0.6rem 1.4rem;
            border-radius: 50px; cursor: pointer; font-size: 0.9rem;
            transition: all 0.2s ease; font-family: inherit; display: none;
          " aria-label="Previous slide">← Back</button>

          <button id="ob-next" onclick="onboardNext()" style="
            background: var(--primary, #00f2fe); border: none;
            color: #0f172a; padding: 0.6rem 1.8rem;
            border-radius: 50px; cursor: pointer; font-size: 0.9rem; font-weight: 700;
            transition: all 0.2s ease; font-family: inherit;
          " aria-label="Next slide">Next →</button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  // Animate in
  requestAnimationFrame(() => {
    overlay.style.opacity = '1';
    const modal = document.getElementById('onboardingModal');
    modal.style.transform = 'translateY(0) scale(1)';
    modal.style.opacity = '1';
  });

  renderSlide(0);
}

function renderSlide(idx) {
  const slide = slides[idx];
  const icon = document.getElementById('ob-icon');
  const title = document.getElementById('ob-title');
  const body = document.getElementById('ob-body');
  const progress = document.getElementById('ob-progress');
  const prevBtn = document.getElementById('ob-prev');
  const nextBtn = document.getElementById('ob-next');
  const dots = document.getElementById('ob-dots');

  // Fade out
  [icon, title, body].forEach(el => el.style.opacity = '0');

  setTimeout(() => {
    icon.textContent = slide.icon;
    title.textContent = slide.title;
    body.textContent = slide.body;

    // Progress
    progress.style.width = `${((idx + 1) / slides.length) * 100}%`;

    // Prev button
    prevBtn.style.display = idx > 0 ? 'inline-block' : 'none';

    // Next/Finish button
    nextBtn.textContent = idx === slides.length - 1 ? '🎉 Finish' : 'Next →';

    // Dots
    dots.innerHTML = '';
    slides.forEach((_, i) => {
      const dot = document.createElement('div');
      dot.style.cssText = `
        width: ${i === idx ? '24px' : '8px'}; height: 8px;
        border-radius: 50px; transition: all 0.3s ease;
        background: ${i === idx ? 'var(--primary, #00f2fe)' : 'rgba(255,255,255,0.2)'};
      `;
      dots.appendChild(dot);
    });

    [icon, title, body].forEach(el => el.style.opacity = '1');
  }, 200);
}

function onboardNext() {
  if (currentSlide < slides.length - 1) {
    currentSlide++;
    renderSlide(currentSlide);
  } else {
    closeOnboarding();
  }
}

function onboardPrev() {
  if (currentSlide > 0) {
    currentSlide--;
    renderSlide(currentSlide);
  }
}

function closeOnboarding() {
  localStorage.setItem(ONBOARDING_KEY, 'true');
  const overlay = document.getElementById('onboardingOverlay');
  if (!overlay) return;
  overlay.style.opacity = '0';
  const modal = document.getElementById('onboardingModal');
  modal.style.transform = 'translateY(20px) scale(0.97)';
  modal.style.opacity = '0';
  setTimeout(() => overlay.remove(), 420);
}

function initOnboarding() {
  if (localStorage.getItem(ONBOARDING_KEY)) return;
  // Delay slightly so page renders first
  setTimeout(buildOnboardingModal, 900);
}

// Keyboard support: Escape to close, Arrow keys to navigate
document.addEventListener('keydown', e => {
  const overlay = document.getElementById('onboardingOverlay');
  if (!overlay) return;
  if (e.key === 'Escape') closeOnboarding();
  if (e.key === 'ArrowRight') onboardNext();
  if (e.key === 'ArrowLeft') onboardPrev();
});

// Expose globally
window.closeOnboarding = closeOnboarding;
window.onboardNext = onboardNext;
window.onboardPrev = onboardPrev;
window.initOnboarding = initOnboarding;
