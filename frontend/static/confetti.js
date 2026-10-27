/**
 * confetti.js – Celebration confetti burst
 * Lightweight, no dependencies.
 */
window.launchConfetti = function (duration = 3000) {
  const canvas = document.createElement('canvas');
  canvas.style.cssText = `
    position:fixed;top:0;left:0;width:100vw;height:100vh;
    pointer-events:none;z-index:999998;
  `;
  document.body.appendChild(canvas);
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const colors = ['#008be3','#0062a3','#ff1389','#ff3d9e','#38bdf8','#ffffff','#d1006a'];
  const pieces = Array.from({ length: 160 }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * -canvas.height,
    w: Math.random() * 10 + 5,
    h: Math.random() * 5 + 3,
    color: colors[Math.floor(Math.random() * colors.length)],
    rot: Math.random() * Math.PI * 2,
    rotSpeed: (Math.random() - 0.5) * 0.2,
    vx: (Math.random() - 0.5) * 3,
    vy: Math.random() * 4 + 2,
    opacity: 1,
  }));

  const start = performance.now();
  function draw(now) {
    const elapsed = now - start;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    pieces.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.rotSpeed;
      if (elapsed > duration * 0.6) p.opacity = Math.max(0, p.opacity - 0.012);
      ctx.save();
      ctx.globalAlpha = p.opacity;
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    });
    if (elapsed < duration + 500) requestAnimationFrame(draw);
    else canvas.remove();
  }
  requestAnimationFrame(draw);
};
