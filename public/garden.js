// Entropy Garden: the generative canvases behind the "video" posts.
// Each canvas starts drawing the first time it scrolls into view, pauses
// while it is off screen, and replays from its seed when it comes back.

const GARDEN_COLORS = {
  bg: '#1e1e2e', growth: '#a6e3a1', glow: '#94e2d5', accent: '#cba6f7', dim: '#45475a'
};

// Canvases wait here until they are first seen, so a long archive does not
// start two hundred animations at once.
const gardenStarter = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (!e.isIntersecting) return;
    const c = e.target;
    gardenStarter.unobserve(c);
    initEntropyGarden(c, c.dataset.algo, Number(c.dataset.seed));
  });
}, { rootMargin: '200px' });

function mountGardens(root) {
  root.querySelectorAll('canvas.garden:not([data-mounted])').forEach(c => {
    c.dataset.mounted = '1';
    const ctx = c.getContext('2d');
    ctx.fillStyle = GARDEN_COLORS.bg;
    ctx.fillRect(0, 0, c.width, c.height);
    gardenStarter.observe(c);
  });
}

function initEntropyGarden(canvas, algo, seed) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.fillStyle = GARDEN_COLORS.bg;
  ctx.fillRect(0, 0, W, H);

  // Simple seeded RNG
  let s = seed;
  const rng = () => { s = (s * 1664525 + 1013904223) & 0xFFFFFFFF; return (s >>> 0) / 0xFFFFFFFF; };

  const generators = { dla, flow_field, cellular, game_of_life };
  const runGen = generators[algo] || generators.dla;

  // Track if we've already set up a re-entry observer
  if (canvas._reentryObserver) canvas._reentryObserver.disconnect();
  const reObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting && canvas._hasLeftView) {
        // Reset and replay
        canvas._hasLeftView = false;
        s = seed;  // reset RNG
        ctx.fillStyle = GARDEN_COLORS.bg;
        ctx.fillRect(0, 0, W, H);
        if (canvas._animFrame) cancelAnimationFrame(canvas._animFrame);
        runGen(ctx, W, H, () => { s = (s * 1664525 + 1013904223) & 0xFFFFFFFF; return (s >>> 0) / 0xFFFFFFFF; }, canvas);
      } else if (!e.isIntersecting) {
        canvas._hasLeftView = true;
      }
    });
  }, { threshold: 0.1 });
  reObs.observe(canvas);
  canvas._reentryObserver = reObs;

  runGen(ctx, W, H, rng, canvas);
}

function dla(ctx, W, H, rng, canvas) {
  // Diffusion-limited aggregation — frost crystal. Walkers are launched on a
  // ring just outside the current crystal (not from the canvas edges), so the
  // crystal visibly grows within seconds instead of sitting as a single dot.
  const scale = 2;
  const gw = Math.floor(W / scale), gh = Math.floor(H / scale);
  const cx = Math.floor(gw / 2), cy = Math.floor(gh / 2);
  const limit = Math.min(cx, cy) - 2;
  const grid = new Uint8Array(gw * gh);
  grid[cy * gw + cx] = 1;
  let maxR = 1;

  const spawn = () => {
    const a = rng() * Math.PI * 2, r = Math.min(maxR + 4, limit);
    return { x: Math.round(cx + Math.cos(a) * r), y: Math.round(cy + Math.sin(a) * r) };
  };
  const particles = [];
  for (let i = 0; i < 400; i++) particles.push(spawn());

  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => { canvas._visible = e.isIntersecting; });
  }, { threshold: 0.1 });
  observer.observe(canvas);
  canvas._visible = true;

  let frame = 0;
  function step() {
    if (!canvas._visible) { canvas._animFrame = requestAnimationFrame(step); return; }
    for (let iter = 0; iter < 30; iter++) {
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += Math.floor(rng() * 3) - 1;
        p.y += Math.floor(rng() * 3) - 1;
        const d2 = (p.x - cx) ** 2 + (p.y - cy) ** 2;
        if (d2 > (maxR + 12) ** 2 || p.x < 1 || p.y < 1 || p.x >= gw - 1 || p.y >= gh - 1) {
          particles[i] = spawn(); continue;   // wandered off — relaunch
        }
        let neighbor = false;
        for (let dy = -1; dy <= 1 && !neighbor; dy++)
          for (let dx = -1; dx <= 1 && !neighbor; dx++)
            if ((dx || dy) && grid[(p.y + dy) * gw + p.x + dx]) neighbor = true;
        if (neighbor) {
          grid[p.y * gw + p.x] = 1;
          const r = Math.sqrt(d2);
          if (r > maxR) maxR = r;
          const dist = r / limit;
          ctx.fillStyle = `hsl(${140 + dist * 80}, 50%, ${60 + (1 - dist) * 20}%)`;
          ctx.fillRect(p.x * scale, p.y * scale, scale, scale);
          particles[i] = spawn();
        }
      }
    }
    frame++;
    if (frame < 2400 && maxR < limit) canvas._animFrame = requestAnimationFrame(step);
  }
  canvas._animFrame = requestAnimationFrame(step);
}

function flow_field(ctx, W, H, rng, canvas) {
  // Perlin-like flow field with particle trails
  const res = 20;
  const cols = Math.ceil(W / res), rows = Math.ceil(H / res);
  // Simple noise grid
  const angles = [];
  for (let i = 0; i < cols * rows; i++) angles.push(rng() * Math.PI * 4);
  // Smooth it
  for (let pass = 0; pass < 3; pass++) {
    for (let y = 1; y < rows - 1; y++) {
      for (let x = 1; x < cols - 1; x++) {
        const i = y * cols + x;
        angles[i] = (angles[i] + angles[i-1] + angles[i+1] + angles[i-cols] + angles[i+cols]) / 5;
      }
    }
  }

  const particles = [];
  for (let i = 0; i < 800; i++) {
    particles.push({ x: rng() * W, y: rng() * H, life: 100 + rng() * 200 });
  }

  ctx.globalAlpha = 0.4;
  let frame = 0;
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => { canvas._visible = e.isIntersecting; });
  }, { threshold: 0.1 });
  observer.observe(canvas);
  canvas._visible = true;

  function step() {
    if (!canvas._visible) { canvas._animFrame = requestAnimationFrame(step); return; }
    // Fade
    ctx.globalAlpha = 0.01;
    ctx.fillStyle = GARDEN_COLORS.bg;
    ctx.fillRect(0, 0, W, H);
    ctx.globalAlpha = 0.6;

    for (const p of particles) {
      const col = Math.floor(p.x / res), row = Math.floor(p.y / res);
      if (col >= 0 && col < cols && row >= 0 && row < rows) {
        const angle = angles[row * cols + col] + frame * 0.002;
        p.x += Math.cos(angle) * 1.5;
        p.y += Math.sin(angle) * 1.5;
      }
      p.life--;
      if (p.life <= 0 || p.x < 0 || p.x > W || p.y < 0 || p.y > H) {
        p.x = rng() * W; p.y = rng() * H; p.life = 100 + rng() * 200;
      }
      const t = p.life / 300;
      ctx.fillStyle = t > 0.5 ? GARDEN_COLORS.growth : GARDEN_COLORS.glow;
      ctx.fillRect(p.x, p.y, 2, 2);
    }
    frame++;
    if (frame < 3000) canvas._animFrame = requestAnimationFrame(step);
  }
  canvas._animFrame = requestAnimationFrame(step);
}

function cellular(ctx, W, H, rng) {
  // Rule 110 cellular automaton, row by row
  const scale = 3;
  const cols = Math.floor(W / scale);
  const rule = 110;
  let row = new Uint8Array(cols);
  row[Math.floor(cols / 2)] = 1; // single seed
  for (let i = 0; i < cols; i++) if (rng() < 0.01) row[i] = 1; // sprinkle

  let y = 0;
  const maxRows = Math.floor(H / scale);
  const colors = [GARDEN_COLORS.bg, GARDEN_COLORS.growth, GARDEN_COLORS.glow, GARDEN_COLORS.accent];

  function drawRow() {
    for (let x = 0; x < cols; x++) {
      if (row[x]) {
        const ci = (x + y) % 3 + 1;
        ctx.fillStyle = colors[ci];
        ctx.fillRect(x * scale, y * scale, scale, scale);
      }
    }
    const next = new Uint8Array(cols);
    for (let x = 0; x < cols; x++) {
      const l = row[(x - 1 + cols) % cols], c = row[x], r = row[(x + 1) % cols];
      const pattern = (l << 2) | (c << 1) | r;
      next[x] = (rule >> pattern) & 1;
    }
    row = next;
    y++;
    if (y < maxRows) setTimeout(drawRow, 25);
  }
  drawRow();
}

function game_of_life(ctx, W, H, rng, canvas) {
  const scale = 4;
  const gw = Math.floor(W / scale), gh = Math.floor(H / scale);
  let grid = new Uint8Array(gw * gh);
  // Random seed ~25%
  for (let i = 0; i < grid.length; i++) grid[i] = rng() < 0.25 ? 1 : 0;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => { canvas._visible = e.isIntersecting; });
  }, { threshold: 0.1 });
  observer.observe(canvas);
  canvas._visible = true;

  let gen = 0;
  function step() {
    if (!canvas._visible) { canvas._animFrame = requestAnimationFrame(step); return; }
    ctx.fillStyle = GARDEN_COLORS.bg;
    ctx.fillRect(0, 0, W, H);

    const next = new Uint8Array(gw * gh);
    for (let y = 0; y < gh; y++) {
      for (let x = 0; x < gw; x++) {
        let n = 0;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          if (dx === 0 && dy === 0) continue;
          const nx = (x + dx + gw) % gw, ny = (y + dy + gh) % gh;
          n += grid[ny * gw + nx];
        }
        const alive = grid[y * gw + x];
        next[y * gw + x] = alive ? (n === 2 || n === 3 ? 1 : 0) : (n === 3 ? 1 : 0);
        if (next[y * gw + x]) {
          ctx.fillStyle = alive ? GARDEN_COLORS.growth : GARDEN_COLORS.glow;
          ctx.fillRect(x * scale, y * scale, scale - 1, scale - 1);
        }
      }
    }
    grid = next;
    gen++;
    if (gen < 1000) setTimeout(() => canvas._animFrame = requestAnimationFrame(step), 80);
  }
  canvas._animFrame = requestAnimationFrame(step);
}

