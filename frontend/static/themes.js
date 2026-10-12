/**
 * themes.js – Nature Wallpaper, Live Motion & Atmospheric Particle Engine
 * Events Booking
 */

(function () {
  'use strict';

  // ─── 1. Curated High-Definition Nature Wallpapers ──────────────────────────
  const natureWallpapers = {
    dynamic: {
      id: 'dynamic',
      name: 'Dynamic by Page',
      icon: '🔄',
      badge: 'Auto',
      desc: 'Automatically applies a tailored nature scene to each page',
      thumb: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=400&q=80'
    },
    aurora: {
      id: 'aurora',
      name: 'Cosmic Aurora',
      icon: '🌌',
      desc: 'Northern lights dancing over starry mountain horizons',
      url: 'https://images.unsplash.com/photo-1531366936337-7c912a4589a7?auto=format&fit=crop&w=2400&q=80',
      thumb: 'https://images.unsplash.com/photo-1531366936337-7c912a4589a7?auto=format&fit=crop&w=400&q=80'
    },
    forest: {
      id: 'forest',
      name: 'Emerald Forest',
      icon: '🌲',
      desc: 'Misty redwoods, pine trees & morning sunbeams',
      url: 'https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=2400&q=80',
      thumb: 'https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=400&q=80'
    },
    mountains: {
      id: 'mountains',
      name: 'Alpine Mountain Peaks',
      icon: '🏔️',
      desc: 'Majestic snow-capped alpine peaks at golden dawn',
      url: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=2400&q=80',
      thumb: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=400&q=80'
    },
    ocean: {
      id: 'ocean',
      name: 'Pacific Ocean Waves',
      icon: '🌊',
      desc: 'Deep turquoise ocean swells, sea foam & tide',
      url: 'https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=2400&q=80',
      thumb: 'https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=400&q=80'
    },
    sunrise: {
      id: 'sunrise',
      name: 'Yosemite Sunrise',
      icon: '🌅',
      desc: 'Golden sunrise mist over granite valley & lake',
      url: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=2400&q=80',
      thumb: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=400&q=80'
    },
    sakura: {
      id: 'sakura',
      name: 'Zen Garden Sakura',
      icon: '🌸',
      desc: 'Tranquil Japanese cherry blossoms & Mt. Fuji pagoda',
      url: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=2400&q=80',
      thumb: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=400&q=80'
    },
    autumn: {
      id: 'autumn',
      name: 'Golden Autumn Sunset',
      icon: '🍂',
      desc: 'Warm golden maple foliage & twilight coastal glow',
      url: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=2400&q=80',
      thumb: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=400&q=80'
    },
    starry: {
      id: 'starry',
      name: 'Starry Milky Way',
      icon: '✨',
      desc: 'Deep celestial starlight & night mountain ridges',
      url: 'https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=2400&q=80',
      thumb: 'https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=400&q=80'
    },
    valley: {
      id: 'valley',
      name: 'Misty Green Valley',
      icon: '🍃',
      desc: 'Lush rolling green hills, morning fog & sky',
      url: 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=2400&q=80',
      thumb: 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=400&q=80'
    },
    thrones: {
      id: 'thrones',
      name: 'Westeros (Game of Thrones)',
      icon: '🐉',
      desc: 'Dragonstone fortress, Valyrian fire & stormy seas',
      url: 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=2400&q=80',
      thumb: 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=400&q=80'
    }
  };

  // Default Nature Wallpaper mapped per page
  const pageNatureDefaults = {
    dashboard: 'aurora',
    history: 'forest',
    event: 'mountains',
    profile: 'ocean',
    settings: 'aurora',
    register: 'sunrise',
    scanner: 'starry',
    verify: 'valley',
    host: 'autumn',
    analytics: 'autumn',
    login: 'sakura',
    admin: 'forest'
  };

  // ─── 2. Page Detection Helper ─────────────────────────────────────────────
  function detectCurrentPage() {
    const path = window.location.pathname.toLowerCase();
    if (path.includes('dashboard') || path === '/' || path === '') return 'dashboard';
    if (path.includes('history') || path.includes('booking')) return 'history';
    if (path.includes('event/')) return 'event';
    if (path.includes('settings')) return 'settings';
    if (path.includes('profile')) return 'profile';
    if (path.includes('register/')) return 'register';
    if (path.includes('scan_ticket') || path.includes('scanner')) return 'scanner';
    if (path.includes('verify')) return 'verify';
    if (path.includes('analytics') || path.includes('host')) return 'analytics';
    if (path.includes('login') || path.includes('forgot')) return 'login';
    if (path.includes('admin')) return 'admin';
    return 'dashboard';
  }

  // ─── 3. Apply Nature Wallpaper ────────────────────────────────────────────
  function applyNatureWallpaper(themeId) {
    const root = document.documentElement;
    const body = document.body;
    const currentPage = detectCurrentPage();

    // Clear all explicit theme classes
    Object.keys(natureWallpapers).forEach(k => {
      body.classList.remove(`theme-nature-${k}`);
    });

    let effectiveTheme = themeId;
    if (!effectiveTheme || effectiveTheme === 'dynamic') {
      effectiveTheme = pageNatureDefaults[currentPage] || 'aurora';
      body.classList.add(`bg-${currentPage}`);
      const bgData = natureWallpapers[effectiveTheme];
      if (bgData && bgData.url) {
        root.style.setProperty('--page-bg-image', `url('${bgData.url}')`);
      }
    } else {
      const bgData = natureWallpapers[effectiveTheme];
      if (bgData && bgData.url) {
        root.style.setProperty('--page-bg-image', `url('${bgData.url}')`);
        body.classList.add(`theme-nature-${effectiveTheme}`);
      }
    }

    // Persist choice in storage
    localStorage.setItem('natureWallpaperTheme', themeId || 'dynamic');

    // Update Modal UI Active States if rendered
    updateNatureModalActiveState(themeId || 'dynamic');

    // Re-spawn particles to match new wallpaper theme if in auto mode
    if (currentParticleType === 'auto') {
      spawnParticles();
    }
  }

  // ─── 4. Color Accent Themes ───────────────────────────────────────────────
  const colorThemes = {
    ocean: {
      '--primary': '#00f2fe',
      '--primary-dark': '#4facfe',
      '--secondary': '#ff0080',
    },
    emerald: {
      '--primary': '#10b981',
      '--primary-dark': '#059669',
      '--secondary': '#06b6d4',
    },
    sunset: {
      '--primary': '#fb923c',
      '--primary-dark': '#f97316',
      '--secondary': '#f43f5e',
    },
    neon: {
      '--primary': '#a78bfa',
      '--primary-dark': '#7c3aed',
      '--secondary': '#ec4899',
    },
    thrones: {
      '--primary': '#f59e0b',
      '--primary-dark': '#d97706',
      '--secondary': '#dc2626',
    },
  };

  function applyColorTheme(themeName) {
    const theme = colorThemes[themeName] || colorThemes['ocean'];
    const root = document.documentElement;
    Object.entries(theme).forEach(([varName, value]) => {
      root.style.setProperty(varName, value);
    });
    localStorage.setItem('selectedColorTheme', themeName);
  }

  // ─── 5. Live Background & Atmospheric Particle Simulation Engine ───────────
  let liveCanvas = null;
  let liveCtx = null;
  let animFrameId = null;
  let particles = [];
  let currentParticleType = 'auto'; // 'auto', 'sakura', 'fireflies', 'starlight', 'leaves', 'mist', 'bubbles', 'off'
  let isTabVisible = true;

  function getEffectiveParticleType() {
    if (currentParticleType !== 'auto') return currentParticleType;
    const currentTheme = localStorage.getItem('natureWallpaperTheme') || 'dynamic';
    let effective = currentTheme;
    if (effective === 'dynamic') {
      effective = pageNatureDefaults[detectCurrentPage()] || 'aurora';
    }
    switch (effective) {
      case 'sakura': return 'sakura';
      case 'aurora':
      case 'starry': return 'starlight';
      case 'forest':
      case 'valley': return 'fireflies';
      case 'autumn': return 'leaves';
      case 'ocean': return 'bubbles';
      case 'sunrise':
      case 'mountains': return 'mist';
      case 'thrones': return 'embers';
      default: return 'starlight';
    }
  }

  function initLiveLayers() {
    if (!document.getElementById('liveBgMotionLayer')) {
      const motionLayer = document.createElement('div');
      motionLayer.id = 'liveBgMotionLayer';
      motionLayer.setAttribute('aria-hidden', 'true');
      document.body.insertBefore(motionLayer, document.body.firstChild);
    }
    if (!document.getElementById('liveParticleCanvas')) {
      liveCanvas = document.createElement('canvas');
      liveCanvas.id = 'liveParticleCanvas';
      liveCanvas.setAttribute('aria-hidden', 'true');
      document.body.insertBefore(liveCanvas, document.body.firstChild);
      liveCtx = liveCanvas.getContext('2d');
      resizeCanvas();
      window.addEventListener('resize', resizeCanvas, { passive: true });
    } else {
      liveCanvas = document.getElementById('liveParticleCanvas');
      liveCtx = liveCanvas.getContext('2d');
    }
  }

  function resizeCanvas() {
    if (!liveCanvas) return;
    liveCanvas.width = window.innerWidth;
    liveCanvas.height = window.innerHeight;
    spawnParticles();
  }

  function spawnParticles() {
    if (!liveCanvas) return;
    const type = getEffectiveParticleType();
    particles = [];
    if (type === 'off') return;

    const w = liveCanvas.width;
    const h = liveCanvas.height;
    let count = 35;
    if (type === 'starlight') count = 45;
    if (type === 'sakura') count = 32;
    if (type === 'fireflies') count = 28;
    if (type === 'leaves') count = 24;
    if (type === 'bubbles') count = 30;
    if (type === 'mist') count = 18;
    if (type === 'embers') count = 36;

    for (let i = 0; i < count; i++) {
      particles.push(createParticle(type, w, h, true));
    }
  }

  function createParticle(type, w, h, randomizeY = false) {
    const startY = randomizeY ? Math.random() * h : (type === 'bubbles' || type === 'embers' ? h + 20 : -20);
    const startX = Math.random() * w;

    if (type === 'sakura') {
      return {
        type: 'sakura',
        x: startX,
        y: startY,
        size: 8 + Math.random() * 8,
        vx: (Math.random() - 0.2) * 1.2 + 0.6,
        vy: 0.8 + Math.random() * 1.2,
        rotation: Math.random() * Math.PI * 2,
        rotSpeed: (Math.random() - 0.5) * 0.03,
        swayPhase: Math.random() * Math.PI * 2,
        swaySpeed: 0.02 + Math.random() * 0.02,
        opacity: 0.4 + Math.random() * 0.45
      };
    } else if (type === 'fireflies') {
      return {
        type: 'fireflies',
        x: startX,
        y: startY,
        size: 2.2 + Math.random() * 2.8,
        vx: (Math.random() - 0.5) * 0.6,
        vy: (Math.random() - 0.5) * 0.6,
        pulsePhase: Math.random() * Math.PI * 2,
        pulseSpeed: 0.03 + Math.random() * 0.04,
        maxAlpha: 0.5 + Math.random() * 0.5,
        color: Math.random() > 0.3 ? '250, 204, 21' : '52, 211, 153'
      };
    } else if (type === 'starlight') {
      return {
        type: 'starlight',
        x: startX,
        y: startY,
        size: 1 + Math.random() * 2.5,
        twinklePhase: Math.random() * Math.PI * 2,
        twinkleSpeed: 0.02 + Math.random() * 0.04,
        vx: (Math.random() - 0.5) * 0.15,
        vy: (Math.random() - 0.5) * 0.15,
        color: Math.random() > 0.4 ? '255, 255, 255' : (Math.random() > 0.5 ? '0, 242, 254' : '167, 139, 250')
      };
    } else if (type === 'leaves') {
      return {
        type: 'leaves',
        x: startX,
        y: startY,
        size: 10 + Math.random() * 10,
        vx: (Math.random() - 0.2) * 1.5 + 0.8,
        vy: 1.0 + Math.random() * 1.5,
        rotation: Math.random() * Math.PI * 2,
        rotSpeed: (Math.random() - 0.5) * 0.04,
        swayPhase: Math.random() * Math.PI * 2,
        swaySpeed: 0.025 + Math.random() * 0.02,
        color: Math.random() > 0.5 ? '245, 158, 11' : (Math.random() > 0.5 ? '239, 68, 68' : '217, 119, 6'),
        opacity: 0.5 + Math.random() * 0.4
      };
    } else if (type === 'bubbles') {
      return {
        type: 'bubbles',
        x: startX,
        y: randomizeY ? Math.random() * h : h + 15,
        size: 3 + Math.random() * 6,
        vx: (Math.random() - 0.5) * 0.5,
        vy: -0.6 - Math.random() * 1.0,
        swayPhase: Math.random() * Math.PI * 2,
        swaySpeed: 0.03 + Math.random() * 0.02,
        opacity: 0.25 + Math.random() * 0.45
      };
    } else if (type === 'embers') {
      return {
        type: 'embers',
        x: startX,
        y: randomizeY ? Math.random() * h : h + 15,
        size: 1.8 + Math.random() * 3.2,
        vx: (Math.random() - 0.5) * 1.0,
        vy: -1.2 - Math.random() * 1.8,
        flickerPhase: Math.random() * Math.PI * 2,
        flickerSpeed: 0.05 + Math.random() * 0.07,
        color: Math.random() > 0.6 ? '245, 158, 11' : (Math.random() > 0.3 ? '239, 68, 68' : '251, 146, 60'),
        opacity: 0.6 + Math.random() * 0.4
      };
    } else { // 'mist'
      return {
        type: 'mist',
        x: startX,
        y: startY,
        size: 40 + Math.random() * 60,
        vx: 0.3 + Math.random() * 0.4,
        vy: (Math.random() - 0.5) * 0.2,
        opacity: 0.08 + Math.random() * 0.12,
        pulsePhase: Math.random() * Math.PI * 2
      };
    }
  }

  function drawParticles() {
    if (!liveCanvas || !liveCtx) {
      animFrameId = requestAnimationFrame(drawParticles);
      return;
    }

    if (!isTabVisible) {
      animFrameId = requestAnimationFrame(drawParticles);
      return;
    }

    const type = getEffectiveParticleType();
    if (type === 'off') {
      liveCtx.clearRect(0, 0, liveCanvas.width, liveCanvas.height);
      animFrameId = requestAnimationFrame(drawParticles);
      return;
    }

    const w = liveCanvas.width;
    const h = liveCanvas.height;
    liveCtx.clearRect(0, 0, w, h);

    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];

      if (p.type === 'sakura') {
        p.swayPhase += p.swaySpeed;
        p.rotation += p.rotSpeed;
        p.x += p.vx + Math.sin(p.swayPhase) * 0.8;
        p.y += p.vy;

        if (p.y > h + 20 || p.x > w + 20 || p.x < -20) {
          particles[i] = createParticle('sakura', w, h, false);
          continue;
        }

        liveCtx.save();
        liveCtx.translate(p.x, p.y);
        liveCtx.rotate(p.rotation);
        liveCtx.beginPath();
        liveCtx.moveTo(0, 0);
        liveCtx.bezierCurveTo(-p.size / 2, -p.size / 2, -p.size, p.size / 3, 0, p.size);
        liveCtx.bezierCurveTo(p.size, p.size / 3, p.size / 2, -p.size / 2, 0, 0);
        liveCtx.fillStyle = `rgba(255, 183, 197, ${p.opacity})`;
        liveCtx.shadowColor = 'rgba(244, 114, 182, 0.4)';
        liveCtx.shadowBlur = 4;
        liveCtx.fill();
        liveCtx.restore();

      } else if (p.type === 'fireflies') {
        p.pulsePhase += p.pulseSpeed;
        const alpha = Math.max(0.05, (Math.sin(p.pulsePhase) * 0.5 + 0.5) * p.maxAlpha);
        p.x += p.vx + Math.sin(p.pulsePhase * 0.5) * 0.4;
        p.y += p.vy + Math.cos(p.pulsePhase * 0.5) * 0.4;

        if (p.x < -10) p.x = w + 10;
        if (p.x > w + 10) p.x = -10;
        if (p.y < -10) p.y = h + 10;
        if (p.y > h + 10) p.y = -10;

        liveCtx.save();
        liveCtx.beginPath();
        liveCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        liveCtx.fillStyle = `rgba(${p.color}, ${alpha})`;
        liveCtx.shadowColor = `rgba(${p.color}, 0.8)`;
        liveCtx.shadowBlur = p.size * 5;
        liveCtx.fill();
        liveCtx.restore();

      } else if (p.type === 'starlight') {
        p.twinklePhase += p.twinkleSpeed;
        const alpha = Math.max(0.1, Math.sin(p.twinklePhase) * 0.45 + 0.55);
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < -10) p.x = w + 10;
        if (p.x > w + 10) p.x = -10;
        if (p.y < -10) p.y = h + 10;
        if (p.y > h + 10) p.y = -10;

        liveCtx.save();
        liveCtx.beginPath();
        liveCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        liveCtx.fillStyle = `rgba(${p.color}, ${alpha * 0.85})`;
        liveCtx.shadowColor = `rgba(${p.color}, 0.9)`;
        liveCtx.shadowBlur = 6;
        liveCtx.fill();
        liveCtx.restore();

      } else if (p.type === 'leaves') {
        p.swayPhase += p.swaySpeed;
        p.rotation += p.rotSpeed;
        p.x += p.vx + Math.sin(p.swayPhase) * 1.2;
        p.y += p.vy;

        if (p.y > h + 25 || p.x > w + 25 || p.x < -25) {
          particles[i] = createParticle('leaves', w, h, false);
          continue;
        }

        liveCtx.save();
        liveCtx.translate(p.x, p.y);
        liveCtx.rotate(p.rotation);
        liveCtx.beginPath();
        liveCtx.ellipse(0, 0, p.size * 0.45, p.size, Math.PI / 4, 0, Math.PI * 2);
        liveCtx.fillStyle = `rgba(${p.color}, ${p.opacity})`;
        liveCtx.shadowColor = 'rgba(245, 158, 11, 0.4)';
        liveCtx.shadowBlur = 4;
        liveCtx.fill();
        liveCtx.restore();

      } else if (p.type === 'bubbles') {
        p.swayPhase += p.swaySpeed;
        p.x += p.vx + Math.sin(p.swayPhase) * 0.5;
        p.y += p.vy;

        if (p.y < -20) {
          particles[i] = createParticle('bubbles', w, h, false);
          continue;
        }

        liveCtx.save();
        liveCtx.beginPath();
        liveCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        liveCtx.fillStyle = `rgba(0, 242, 254, ${p.opacity * 0.35})`;
        liveCtx.strokeStyle = `rgba(255, 255, 255, ${p.opacity * 0.6})`;
        liveCtx.lineWidth = 1;
        liveCtx.shadowColor = 'rgba(0, 242, 254, 0.5)';
        liveCtx.shadowBlur = 5;
        liveCtx.fill();
        liveCtx.stroke();
        liveCtx.restore();

      } else if (p.type === 'mist') {
        p.pulsePhase += 0.01;
        p.x += p.vx;
        p.y += p.vy;

        if (p.x > w + p.size) p.x = -p.size;

        const radGrad = liveCtx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size);
        radGrad.addColorStop(0, `rgba(255, 255, 255, ${p.opacity})`);
        radGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');

        liveCtx.save();
        liveCtx.fillStyle = radGrad;
        liveCtx.beginPath();
        liveCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        liveCtx.fill();
        liveCtx.restore();

      } else if (p.type === 'embers') {
        p.flickerPhase += p.flickerSpeed;
        p.x += p.vx + Math.sin(p.flickerPhase) * 0.6;
        p.y += p.vy;

        if (p.y < -15 || p.x > w + 20 || p.x < -20) {
          particles[i] = createParticle('embers', w, h, false);
          continue;
        }

        const alpha = Math.max(0.2, (Math.sin(p.flickerPhase) * 0.35 + 0.65) * p.opacity);
        liveCtx.save();
        liveCtx.beginPath();
        liveCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        liveCtx.fillStyle = `rgba(${p.color}, ${alpha})`;
        liveCtx.shadowColor = `rgba(${p.color}, 0.9)`;
        liveCtx.shadowBlur = p.size * 5;
        liveCtx.fill();
        liveCtx.restore();
      }
    }

    animFrameId = requestAnimationFrame(drawParticles);
  }

  function setLiveMotion(enable) {
    const isMotion = enable !== false;
    if (isMotion) {
      document.body.classList.add('live-motion-active');
    } else {
      document.body.classList.remove('live-motion-active');
    }
    localStorage.setItem('liveMotionEnabled', isMotion ? 'true' : 'false');
  }

  function setLiveParticles(mode) {
    currentParticleType = mode || 'auto';
    localStorage.setItem('liveParticleMode', currentParticleType);
    spawnParticles();
  }

  document.addEventListener('visibilitychange', () => {
    isTabVisible = !document.hidden;
  });

  // ─── 6. Nature Wallpaper Modal Switcher UI ────────────────────────────────
  function injectThemeCoreStyles() {
    if (document.getElementById('themes-dynamic-style')) return;
    const style = document.createElement('style');
    style.id = 'themes-dynamic-style';
    style.textContent = `
      .nature-theme-btn {
        background: rgba(16, 185, 129, 0.15) !important;
        color: #10b981 !important;
        border: 1px solid rgba(16, 185, 129, 0.45) !important;
        padding: 0.42rem 0.9rem !important;
        border-radius: 50px !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        backdrop-filter: blur(8px) !important;
        margin: 0 !important;
        outline: none !important;
        box-sizing: border-box !important;
        flex-shrink: 0 !important;
        white-space: nowrap !important;
      }
      .nature-theme-btn:hover {
        background: #10b981 !important;
        color: #0f172a !important;
        border-color: #10b981 !important;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.45) !important;
        transform: translateY(-1px) !important;
      }
      body.light-mode .nature-theme-btn {
        background: #ecfdf5 !important;
        color: #065f46 !important;
        border-color: #a7f3d0 !important;
      }
      body.light-mode .nature-theme-btn:hover {
        background: #10b981 !important;
        color: #ffffff !important;
        border-color: #10b981 !important;
      }
      .nature-modal-overlay {
        display: none;
        position: fixed !important;
        inset: 0 !important;
        background: rgba(0, 0, 0, 0.8) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        z-index: 999999 !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 1.5rem !important;
        box-sizing: border-box !important;
      }
      .nature-modal-content {
        background: #0f172a !important;
        backdrop-filter: blur(24px) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 20px !important;
        padding: 2rem !important;
        max-width: 760px !important;
        width: 100% !important;
        max-height: 85vh !important;
        overflow-y: auto !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7) !important;
        box-sizing: border-box !important;
      }
      body.light-mode .nature-modal-content {
        background: #ffffff !important;
        border-color: rgba(0, 0, 0, 0.1) !important;
        box-shadow: 0 20px 45px rgba(0, 0, 0, 0.15) !important;
      }
      .nature-grid {
        display: grid !important;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)) !important;
        gap: 1rem !important;
        margin-top: 1.4rem !important;
      }
      .nature-card {
        position: relative !important;
        border-radius: 14px !important;
        overflow: hidden !important;
        cursor: pointer !important;
        border: 2px solid rgba(255, 255, 255, 0.12) !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        background: rgba(0, 0, 0, 0.4) !important;
        height: 115px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-end !important;
        padding: 0.85rem !important;
        box-sizing: border-box !important;
      }
      .nature-card.active {
        border-color: #00f2fe !important;
        box-shadow: 0 0 20px rgba(0, 242, 254, 0.5) !important;
      }
      .nature-card img.nature-card-bg {
        position: absolute !important;
        inset: 0 !important;
        width: 100% !important;
        height: 100% !important;
        object-fit: cover !important;
        transition: transform 0.4s ease !important;
        z-index: 1 !important;
      }
      .nature-card:hover img.nature-card-bg {
        transform: scale(1.08) !important;
      }
      .nature-card::before {
        content: '' !important;
        position: absolute !important;
        inset: 0 !important;
        background: linear-gradient(to top, rgba(0, 0, 0, 0.85) 0%, rgba(0, 0, 0, 0.25) 60%, transparent 100%) !important;
        z-index: 2 !important;
      }
      .nature-card-info {
        position: relative !important;
        z-index: 3 !important;
      }
      .nature-card-title {
        color: white !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        margin-bottom: 2px !important;
      }
      .nature-card-desc {
        color: rgba(255, 255, 255, 0.7) !important;
        font-size: 0.72rem !important;
        line-height: 1.2 !important;
      }
      .nature-active-badge {
        position: absolute !important;
        top: 8px !important;
        right: 8px !important;
        background: #00f2fe !important;
        color: #0f172a !important;
        font-size: 0.68rem !important;
        font-weight: 800 !important;
        padding: 2px 7px !important;
        border-radius: 6px !important;
        z-index: 4 !important;
        text-transform: uppercase !important;
      }
    `;
    document.head.appendChild(style);
  }

  function buildNatureModal() {
    injectThemeCoreStyles();
    if (document.getElementById('natureWallpaperModal')) return;

    const modalOverlay = document.createElement('div');
    modalOverlay.id = 'natureWallpaperModal';
    modalOverlay.className = 'nature-modal-overlay';

    modalOverlay.innerHTML = `
      <div class="nature-modal-content">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
          <div>
            <h2 style="font-family: var(--font-heading); color: white; font-size: 1.5rem; margin: 0; display: flex; align-items: center; gap: 8px;">
              🌿 Nature Background Wallpapers
            </h2>
            <p style="color: var(--text-muted); font-size: 0.88rem; margin-top: 4px;">
              Select a nature scene or let the system automatically switch backgrounds per page.
            </p>
          </div>
          <button type="button" id="closeNatureModalBtn" style="background: none; border: none; color: var(--text-muted); font-size: 1.8rem; cursor: pointer; line-height: 1; padding: 0 4px;">&times;</button>
        </div>

        <div class="nature-grid" id="natureCardsGrid">
          ${Object.values(natureWallpapers).map(wp => `
            <div class="nature-card" data-theme-id="${wp.id}" onclick="window.selectNatureTheme('${wp.id}')">
              <img src="${wp.thumb}" alt="${wp.name}" class="nature-card-bg" loading="lazy">
              ${wp.badge ? `<span class="nature-active-badge">${wp.badge}</span>` : ''}
              <div class="nature-card-info">
                <div class="nature-card-title">${wp.icon} ${wp.name}</div>
                <div class="nature-card-desc">${wp.desc}</div>
              </div>
            </div>
          `).join('')}
        </div>

        <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--glass-border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
          <span style="color: var(--text-muted); font-size: 0.8rem;">
            💡 Saved to your browser preferences.
          </span>
          <button type="button" onclick="window.closeNatureModal()" class="register-btn-sm" style="background: var(--primary); color: #0f172a; padding: 0.5rem 1.4rem; font-weight: 700; border-radius: 8px;">
            Done
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modalOverlay);

    // Event listeners
    const closeBtn = document.getElementById('closeNatureModalBtn');
    if (closeBtn) closeBtn.onclick = window.closeNatureModal;

    modalOverlay.onclick = (e) => {
      if (e.target === modalOverlay) window.closeNatureModal();
    };
  }

  function updateNatureModalActiveState(activeId) {
    const grid = document.getElementById('natureCardsGrid');
    if (!grid) return;
    grid.querySelectorAll('.nature-card').forEach(card => {
      const cardId = card.getAttribute('data-theme-id');
      if (cardId === activeId) {
        card.classList.add('active');
      } else {
        card.classList.remove('active');
      }
    });
  }

  // ─── 7. Global Window Handlers ────────────────────────────────────────────
  window.openNatureModal = function () {
    buildNatureModal();
    const currentTheme = localStorage.getItem('natureWallpaperTheme') || 'dynamic';
    updateNatureModalActiveState(currentTheme);
    const modal = document.getElementById('natureWallpaperModal');
    if (modal) modal.style.display = 'flex';
  };

  window.closeNatureModal = function () {
    const modal = document.getElementById('natureWallpaperModal');
    if (modal) modal.style.display = 'none';
  };

  window.selectNatureTheme = function (themeId) {
    applyNatureWallpaper(themeId);
    if (window.showToast) {
      const name = (natureWallpapers[themeId] || {}).name || themeId;
      window.showToast(`🌿 Wallpaper updated: ${name}`, 'success', 2000);
    }
  };

  window.toggleLiveMotion = function (enable) {
    setLiveMotion(enable);
  };

  window.setLiveParticleMode = function (mode) {
    setLiveParticles(mode);
  };

  window.getLiveBackgroundSettings = function () {
    return {
      motionEnabled: localStorage.getItem('liveMotionEnabled') !== 'false',
      particleMode: localStorage.getItem('liveParticleMode') || 'auto'
    };
  };

  // ─── 8. Initialization ────────────────────────────────────────────────────
  function init() {
    injectThemeCoreStyles();
    initLiveLayers();

    const savedWallpaper = localStorage.getItem('natureWallpaperTheme') || 'dynamic';
    applyNatureWallpaper(savedWallpaper);

    const savedColor = localStorage.getItem('selectedColorTheme') || 'ocean';
    applyColorTheme(savedColor);

    const isMotion = localStorage.getItem('liveMotionEnabled') !== 'false';
    setLiveMotion(isMotion);

    const particleMode = localStorage.getItem('liveParticleMode') || 'auto';
    setLiveParticles(particleMode);

    drawParticles();
  }

  // Run on initial load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose API
  window.natureWallpapers = natureWallpapers;
  window.applyNatureWallpaper = applyNatureWallpaper;
  window.applyColorTheme = applyColorTheme;
})();
