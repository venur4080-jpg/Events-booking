/**
 * animations.js – High-Performance Helical Screw Thread & Motion Suite
 * Powered by Motion (motion.dev / Framer Motion Engine)
 * Event Management System
 */

(function () {
  'use strict';

  // ─── 1. Motion CDN Loader & Resilience Fallback ─────────────────────────────
  const MOTION_CDN_URL = 'https://cdn.jsdelivr.net/npm/motion@latest/dist/motion.js';

  function loadMotionLibrary(callback) {
    if (window.Motion) {
      if (typeof callback === 'function') callback(window.Motion);
      return;
    }

    let existingScript = document.querySelector(`script[src*="motion@latest"]`) || 
                         document.querySelector(`script[src*="motion/dist"]`);
    if (existingScript) {
      existingScript.addEventListener('load', () => {
        if (typeof callback === 'function') callback(window.Motion);
      });
      return;
    }

    const script = document.createElement('script');
    script.src = MOTION_CDN_URL;
    script.async = true;
    script.crossOrigin = 'anonymous';

    script.onload = () => {
      console.log('⚡ Motion (Framer Motion Engine) loaded successfully.');
      if (typeof callback === 'function') callback(window.Motion);
    };

    script.onerror = () => {
      console.warn('⚠️ Motion CDN unavailable. Falling back to native Web Animations & CSS springs.');
      if (typeof callback === 'function') callback(null);
    };

    document.head.appendChild(script);
  }

  // ─── 2. Ripple Micro-Interaction ───────────────────────────────────────────
  function createRipple(event) {
    const button = event.currentTarget;
    if (!button) return;
    const circle = document.createElement('span');
    const diameter = Math.max(button.clientWidth, button.clientHeight);
    const radius = diameter / 2;
    const rect = button.getBoundingClientRect();
    circle.style.cssText = `
      width: ${diameter}px; height: ${diameter}px;
      left: ${event.clientX - rect.left - radius}px;
      top: ${event.clientY - rect.top - radius}px;
      position: absolute; border-radius: 50%;
      background: rgba(255,255,255,0.28);
      transform: scale(0); animation: motion-ripple-anim 0.55s cubic-bezier(0.16, 1, 0.3, 1);
      pointer-events: none;
      z-index: 10;
    `;
    const existing = button.querySelector('.motion-ripple-span');
    if (existing) existing.remove();
    circle.classList.add('motion-ripple-span');
    button.style.position = button.style.position || 'relative';
    button.style.overflow = 'hidden';
    button.appendChild(circle);
    circle.addEventListener('animationend', () => circle.remove());
  }

  if (!document.getElementById('motion-suite-styles')) {
    const style = document.createElement('style');
    style.id = 'motion-suite-styles';
    style.textContent = `
      @keyframes motion-ripple-anim { to { transform: scale(4); opacity: 0; } }
      .motion-hover-target { will-change: transform; }
      .motion-spring-modal { will-change: transform, opacity; }
    `;
    document.head.appendChild(style);
  }

  function attachRipples() {
    document.querySelectorAll(`
      button:not(:disabled),
      input[type="button"]:not(:disabled),
      input[type="submit"]:not(:disabled),
      [role="button"],
      .btn,
      .btn-primary, 
      .btn-secondary,
      .btn-danger,
      .btn-danger-solid,
      .btn-warning,
      .btn-warning-outline,
      .btn-success,
      .card-btn-action:not([disabled]),
      .btn-domain-link,
      .btn-edit-link,
      .btn-delete-link,
      .register-btn, 
      .register-btn-sm, 
      .unregister-btn,
      .carousel-btn, 
      .filter-tab-btn,
      .nature-theme-btn,
      .btn-auth,
      .btn-past-events,
      .back-btn-unified,
      .category-back-btn,
      .nav-btn-dash,
      .logout-btn-unique,
      .theme-toggle-btn,
      .calendar-nav-btn,
      .invite-btn,
      .view-toggle-btn,
      .btn-clear-category,
      .unique-save-btn,
      .color-theme-btn,
      .particle-mode-chip,
      .control-pill-btn,
      .csv-btn,
      #chatbot-trigger,
      #chatbot-send,
      #notifBell
    `).forEach(btn => {
      btn.removeEventListener('click', createRipple);
      btn.addEventListener('click', createRipple);
    });
  }

  // ─── 3. Framer Motion Gesture Engine (whileHover & whileTap) ────────────────
  function attachMotionGestures() {
    const Motion = window.Motion;
    const interactiveSelectors = `
      button:not(:disabled),
      input[type="button"]:not(:disabled),
      input[type="submit"]:not(:disabled),
      [role="button"],
      .btn,
      .btn-primary, 
      .btn-secondary,
      .btn-danger,
      .btn-danger-solid,
      .btn-warning,
      .btn-warning-outline,
      .btn-success,
      .card-btn-action:not([disabled]),
      .btn-domain-link,
      .btn-edit-link,
      .btn-delete-link,
      .register-btn, 
      .register-btn-sm, 
      .unregister-btn,
      .filter-tab-btn, 
      .carousel-btn, 
      .nature-theme-btn, 
      .category-pill, 
      .tag-pill, 
      .btn-auth,
      .btn-past-events,
      .action-pill-btn,
      .back-btn-unified,
      .category-back-btn,
      .nav-btn-dash,
      .logout-btn-unique,
      .theme-toggle-btn,
      .calendar-nav-btn,
      .invite-btn,
      .view-toggle-btn,
      .btn-clear-category,
      .unique-save-btn,
      .color-theme-btn,
      .particle-mode-chip,
      .control-pill-btn,
      .csv-btn,
      #chatbot-trigger,
      #chatbot-send,
      #notifBell
    `;

    document.querySelectorAll(interactiveSelectors).forEach(el => {
      if (el.__motionGestureAttached) return;
      el.__motionGestureAttached = true;
      el.classList.add('motion-hover-target');

      // Hover In (whileHover)
      el.addEventListener('mouseenter', () => {
        if (Motion && Motion.animate) {
          try {
            Motion.animate(el, { 
              scale: 1.04, 
              y: -2 
            }, { 
              duration: 0.22,
              easing: 'ease-out'
            });
          } catch(e) {}
        }
      });

      // Hover Out
      el.addEventListener('mouseleave', () => {
        if (Motion && Motion.animate) {
          try {
            Motion.animate(el, { 
              scale: 1, 
              y: 0 
            }, { 
              duration: 0.22,
              easing: 'ease-out'
            });
          } catch(e) {}
        }
      });

      // Tap / Press (whileTap)
      el.addEventListener('pointerdown', () => {
        if (Motion && Motion.animate) {
          try {
            Motion.animate(el, { 
              scale: 0.94 
            }, { 
              duration: 0.12,
              easing: 'ease-out'
            });
          } catch(e) {}
        }
      });

      // Tap Release
      el.addEventListener('pointerup', () => {
        if (Motion && Motion.animate) {
          try {
            Motion.animate(el, { 
              scale: 1.04 
            }, { 
              duration: 0.18,
              easing: 'ease-out'
            });
          } catch(e) {}
        }
      });
    });
  }

  // ─── 4. Scroll Reveal with Stagger & Spring Physics ────────────────────────
  let scrollObserver = null;

  function initScrollReveal() {
    const Motion = window.Motion;

    if (Motion && Motion.inView) {
      const targets = document.querySelectorAll(`
        .event-card:not(.helix-motion-card), 
        .booking-card, 
        .summary-stat-box, 
        .login-card, 
        .verify-card, 
        .scanner-card, 
        .detail-card, 
        .metric-card, 
        .chart-card, 
        .events-table-card, 
        .feed-item, 
        .hero-section, 
        .filter-search-bar, 
        .form-container, 
        .profile-card,
        .reveal-on-scroll
      `);

      targets.forEach((el, index) => {
        if (el.__motionInViewAttached) return;
        el.__motionInViewAttached = true;

        try {
          Motion.inView(el, (info) => {
            const targetEl = (info && info.target) ? info.target : (info instanceof Element ? info : el);
            if (!targetEl) return;
            const delay = (index % 6) * 0.05;
            Motion.animate(targetEl, { 
              opacity: [0, 1], 
              y: [32, 0],
              scale: [0.96, 1]
            }, { 
              delay: delay,
              duration: 0.55,
              easing: 'ease-out'
            });
            if (targetEl.classList) targetEl.classList.add('is-revealed');
          }, { margin: '0px 0px -40px 0px' });
        } catch(e) {}
      });
      return;
    }

    // Fallback: IntersectionObserver with CSS Spring Transitions
    if (!('IntersectionObserver' in window)) {
      document.querySelectorAll('.reveal-on-scroll, .event-card:not(.helix-motion-card), .booking-card, .summary-stat-box, .metric-card, .chart-card').forEach(el => {
        el.classList.add('is-revealed');
      });
      return;
    }

    if (scrollObserver) {
      scrollObserver.disconnect();
    }

    scrollObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, {
      root: null,
      rootMargin: '0px 0px -40px 0px',
      threshold: 0.08
    });

    scanAndObserveElements();
  }

  function scanAndObserveElements() {
    const targets = document.querySelectorAll(`
      .event-card:not(.helix-motion-card), 
      .booking-card, 
      .summary-stat-box, 
      .login-card, 
      .verify-card, 
      .scanner-card, 
      .detail-card, 
      .metric-card, 
      .chart-card, 
      .events-table-card, 
      .feed-item, 
      .hero-section, 
      .filter-search-bar, 
      .form-container, 
      .profile-card,
      .reveal-on-scroll
    `);

    const containers = new Set();
    targets.forEach(el => {
      if (!el.classList.contains('reveal-on-scroll')) {
        el.classList.add('reveal-on-scroll');
      }
      if (el.parentElement) {
        containers.add(el.parentElement);
      }
      if (scrollObserver && !el.classList.contains('is-revealed')) {
        scrollObserver.observe(el);
      }
    });

    containers.forEach(parent => {
      const children = parent.querySelectorAll(':scope > .reveal-on-scroll:not(.is-revealed)');
      children.forEach((child, index) => {
        const staggerIdx = Math.min((index % 8) + 1, 8);
        child.classList.add(`stagger-${staggerIdx}`);
      });
    });
  }

  // ─── 5. Ultra-Smooth Screw Thread Engine (Zero Reflows / 60-120 FPS) ───
  let helixRAF = null;
  let isHelixTicking = false;
  let cachedRows = [];
  let cachedContainer = null;

  function refreshHelixCache() {
    cachedContainer = document.getElementById('pastEventsContainer');
    if (cachedContainer) {
      cachedRows = Array.from(cachedContainer.querySelectorAll('.helix-thread-row'));
    } else {
      cachedRows = [];
    }
  }

  function updateHelixMotionPhysics() {
    if (!cachedContainer) refreshHelixCache();
    if (!cachedContainer || cachedContainer.style.display === 'none' || cachedRows.length === 0) {
      isHelixTicking = false;
      return;
    }

    const scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
    const isMobile = window.innerWidth <= 820;
    // Calibrated cylinder radius for tight, centered symmetrical screw thread
    const radiusX = isMobile ? 45 : 160; // px
    const radiusZ = isMobile ? 45 : 120; // px
    
    // Smooth screw thread rotation driven by scroll position
    const scrollAngle = scrollY * 0.25; // degrees

    for (let i = 0; i < cachedRows.length; i++) {
      const row = cachedRows[i];
      if (row.style.display === 'none') continue;
      const card = row.querySelector('.helix-motion-card');
      if (!card) continue;

      // Ensure card is always fully visible and rendered
      if (card.style.visibility === 'hidden') {
        card.style.visibility = 'visible';
      }

      // Circular Helical Coordinates (90 deg step per pitch)
      const threadAngle = (i * 90) + scrollAngle;
      const rad = (threadAngle * Math.PI) / 180;

      const xPos = Math.sin(rad) * radiusX;
      const zDepth = Math.cos(rad) * radiusZ; // +Z is front, -Z is back

      // Gentle sinusoidal face curvature (always facing reader)
      const rotY = Math.sin(rad) * 14; // -14deg (left) to +14deg (right)
      // Helical screw pitch inclination tilt
      const rotX = Math.cos(rad) * 3.5; // -3.5deg to +3.5deg

      // Normalized depth (0 = furthest back, 1 = closest front)
      const normalizedZ = (zDepth + radiusZ) / (radiusZ * 2);
      const scale = 0.94 + (normalizedZ * 0.08); // 0.94 (back) -> 1.02 (front)
      const opacity = 0.85 + (normalizedZ * 0.15); // 0.85 (back) -> 1.00 (front)
      const zIndex = Math.round(normalizedZ * 100 + 10);

      // Apply 100% GPU-composited transform (0 layout, 0 paint)
      card.style.transform = `translate3d(${xPos.toFixed(1)}px, 0px, ${zDepth.toFixed(1)}px) rotateY(${rotY.toFixed(1)}deg) rotateX(${rotX.toFixed(1)}deg) scale(${scale.toFixed(3)})`;
      card.style.opacity = opacity.toFixed(2);
      row.style.zIndex = zIndex;
    }

    isHelixTicking = false;
  }

  function requestHelixUpdate() {
    if (!isHelixTicking) {
      isHelixTicking = true;
      helixRAF = requestAnimationFrame(updateHelixMotionPhysics);
    }
  }

  function triggerHelixEntrance() {
    refreshHelixCache();
    updateHelixMotionPhysics();
    requestHelixUpdate();
  }

  // ─── 6. Parallax Magnetic Tilt with Spring Recovery ────────────────────
  function attachTiltEffect() {
    document.querySelectorAll('.event-card:not(.helix-motion-card), .booking-card').forEach(card => {
      if (card.__hasTilt) return;
      card.__hasTilt = true;

      let bounds;
      function updateBounds() {
        bounds = card.getBoundingClientRect();
      }

      card.addEventListener('mouseenter', () => {
        updateBounds();
        card.style.transition = 'none';
      });

      card.addEventListener('mousemove', e => {
        if (!bounds) updateBounds();
        const x = e.clientX - bounds.left - bounds.width / 2;
        const y = e.clientY - bounds.top - bounds.height / 2;
        const rotX = -(y / bounds.height) * 8;
        const rotY = (x / bounds.width) * 8;
        card.style.transform = `perspective(1000px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) translateY(-8px) scale(1.018)`;
      });

      card.addEventListener('mouseleave', () => {
        const Motion = window.Motion;
        if (Motion && Motion.animate) {
          try {
            Motion.animate(card, { 
              transform: 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px) scale(1)' 
            }, { 
              duration: 0.4,
              easing: 'ease-out'
            });
          } catch(e) {
            card.style.transform = '';
          }
        } else {
          card.style.transform = '';
          card.style.transition = 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
        }
      });
    });
  }

  // ─── 7. Passive Scroll Listener & Elevation ────────────────────────────────
  function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');

    window.addEventListener('scroll', () => {
      if (navbar) {
        if (window.scrollY > 15) {
          navbar.classList.add('scrolled');
        } else {
          navbar.classList.remove('scrolled');
        }
      }

      // High-performance RAF scroll update
      requestHelixUpdate();
    }, { passive: true });

    if (navbar && window.scrollY > 15) {
      navbar.classList.add('scrolled');
    }
  }

  // ─── 8. Animated Number Counters with Spring Easing ───────────────────────
  function initCounters() {
    document.querySelectorAll('[data-counter], #totalCount, #activeCount, #cancelledCount, #upcomingCount, #pastCount').forEach(el => {
      const textVal = parseInt(el.textContent.replace(/[^0-9]/g, ''), 10);
      if (isNaN(textVal) || textVal <= 0 || el.__animatedCounter) return;

      const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            el.__animatedCounter = true;
            animateCounter(el, textVal, 950);
            obs.disconnect();
          }
        });
      }, { threshold: 0.25 });
      observer.observe(el);
    });
  }

  function animateCounter(el, target, duration = 950) {
    const start = performance.now();
    function step(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3.5);
      el.textContent = Math.floor(target * eased);
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.textContent = target;
      }
    }
    requestAnimationFrame(step);
  }

  // ─── 9. Modal Spring Pop-in Helper ────────────────────────────────────────
  function animateModalOpen(modalElement) {
    if (!modalElement) return;
    const Motion = window.Motion;
    const content = modalElement.querySelector('.modal-content, .glass-panel') || modalElement;

    if (Motion && Motion.animate) {
      try {
        Motion.animate(content, { 
          opacity: [0, 1], 
          scale: [0.88, 1],
          y: [20, 0]
        }, { 
          duration: 0.35,
          easing: 'ease-out'
        });
      } catch(e) {}
    }
  }

  // ─── 10. Dynamic DOM Mutation Watcher ──────────────────────────────────────
  function initDOMWatcher() {
    const observer = new MutationObserver(() => {
      refreshHelixCache();
      scanAndObserveElements();
      attachRipples();
      attachMotionGestures();
      attachTiltEffect();
      requestHelixUpdate();
    });

    const root = document.querySelector('main') || document.body;
    if (root) {
      observer.observe(root, { childList: true, subtree: true });
    }
  }

  // ─── 11. Global Initialization & Public API ───────────────────────────────
  function initAll() {
    refreshHelixCache();
    attachRipples();
    initNavbarScroll();
    attachTiltEffect();
    initCounters();
    initDOMWatcher();

    // Load Motion and initialize spring reveals & gestures
    loadMotionLibrary(() => {
      initScrollReveal();
      attachMotionGestures();
      requestHelixUpdate();
    });
  }

  // Expose global MotionSuite API
  window.MotionSuite = {
    get Motion() { return window.Motion; },
    animate: (target, keyframes, options) => {
      if (window.Motion && window.Motion.animate) {
        return window.Motion.animate(target, keyframes, options);
      }
    },
    inView: (target, onEnter, options) => {
      if (window.Motion && window.Motion.inView) {
        return window.Motion.inView(target, onEnter, options);
      }
    },
    animateModal: animateModalOpen,
    triggerHelixEntrance: triggerHelixEntrance,
    updateHelixMotion: updateHelixMotionPhysics,
    reInit: function () {
      refreshHelixCache();
      scanAndObserveElements();
      attachRipples();
      attachMotionGestures();
      attachTiltEffect();
      initScrollReveal();
      requestHelixUpdate();
    }
  };

  window.reInitAnimations = window.MotionSuite.reInit;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
