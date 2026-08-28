<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Star Mission All In One</title>
  <style>
    :root {
      color-scheme: dark;
      background: #0b1020;
    }

    * {
      box-sizing: border-box;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
    }

    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background:
        radial-gradient(circle at top, #182247 0%, #0b1020 50%, #05070e 100%);
      font-family: Arial, Helvetica, sans-serif;
      overflow: hidden;
    }

    #wrap {
      width: min(100vw, 480px);
      padding: 8px;
    }

    canvas {
      display: block;
      width: 100%;
      height: auto;
      aspect-ratio: 3 / 4;
      background: #101426;
      border: 2px solid rgba(255, 255, 255, 0.45);
      border-radius: 16px;
      box-shadow: 0 18px 65px rgba(0, 0, 0, 0.55);
      touch-action: none;
    }

    .hint {
      color: rgba(255, 255, 255, 0.68);
      font-size: 12px;
      text-align: center;
      margin: 8px 0 0;
      line-height: 1.35;
    }
  </style>
</head>
<body>
  <main id="wrap">
    <canvas id="game" width="480" height="640" aria-label="Star Mission game"></canvas>
    <p class="hint">
      Keyboard: ← → to move, Space to fire, S to open shop.<br>
      Controller: left stick to move, button 0 to fire.
    </p>
  </main>

  <script>
    "use strict";

    // ------------------------------------------------------------
    // Canvas / constants
    // ------------------------------------------------------------
    const canvas = document.getElementById("game");
    const ctx = canvas.getContext("2d");

    const W = 480;
    const H = 640;

    const WHITE = "#ffffff";
    const BLACK = "#000000";
    const BLUE = "#101426";
    const GREEN = "#00d26e";
    const RED = "#e64646";
    const GOLD = "#ffd75a";
    const GRAY = "#64646e";
    const CYAN = "#5ae6ff";
    const BROWN = "#8c5f37";
    const PINK = "#ff82b9";
    const PURPLE = "#a06eff";
    const ORANGE = "#ffaa46";

    const WAVE_SIZE = 4;
    const WAVE_PAUSE_MS = 10000;
    const WAVE_ACTIVE_MS = 4500;
    const BOSS_EVERY = 5;
    const SHIELD_DURATION = 25000;
    const SAVE_KEY = "starMissionSave";

    const QUESTS = [
      ["Kill 5", 5],
      ["Kill 10", 10],
      ["Kill 25", 25],
      ["Survive 60s", 60],
      ["Survive 300s", 300]
    ];

    const SHOP_ITEMS = [
      ["Bullet Speed +1", 15, "bullet_speed"],
      ["Fire Rate +1", 20, "fire_rate"],
      ["Max Health +1", 25, "max_health"],
      ["Move Speed +1", 15, "move_speed"],
      ["Shield 25s", 30, "shield"]
    ];

    const MAPS = [
      { bg: "#101426", stars: "#5ae6ff", accent: "#ff82b9", planet: "#464678" },
      { bg: "#121c1c", stars: "#ffd75a", accent: "#5ae6ff", planet: "#376e55" },
      { bg: "#201228", stars: "#a06eff", accent: "#ffaa46", planet: "#644682" },
      { bg: "#141e30", stars: "#ffffff", accent: "#82ffb4", planet: "#3c5f8c" }
    ];

    // ------------------------------------------------------------
    // Utility functions
    // ------------------------------------------------------------
    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    function randomInt(min, max) {
      return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    function choose(items) {
      return items[Math.floor(Math.random() * items.length)];
    }

    function weightedChoice() {
      const roll = Math.random() * 100;
      if (roll < 60) return "normal";
      if (roll < 85) return "fast";
      return "tank";
    }

    function pointInRect(x, y, rect) {
      return x >= rect.x && x <= rect.x + rect.w &&
             y >= rect.y && y <= rect.y + rect.h;
    }

    function rectsOverlap(a, b) {
      return a.x < b.x + b.w &&
             a.x + a.w > b.x &&
             a.y < b.y + b.h &&
             a.y + a.h > b.y;
    }

    function now() {
      return performance.now();
    }

    // ------------------------------------------------------------
    // Sound
    // ------------------------------------------------------------
    const sounds = {};

    function loadSound(name, file) {
      const audio = new Audio(file);
      audio.preload = "auto";
      sounds[name] = audio;
    }

    function playSound(name) {
      const sound = sounds[name];
      if (!sound || !saveData.sound) return;

      try {
        const copy = sound.cloneNode();
        copy.volume = 0.45;
        copy.play().catch(() => {});
      } catch (_) {}
    }

    loadSound("shoot", "shoot.wav");
    loadSound("hit", "hit.wav");
    loadSound("coin", "coin.wav");
    loadSound("upgrade", "upgrade.wav");
    loadSound("boom", "boom.wav");

    // ------------------------------------------------------------
    // Save data
    // ------------------------------------------------------------
    function defaultSave() {
      return {
        best_score: 0,
        coins: 0,
        upgrades: {
          bullet_speed: 0,
          fire_rate: 0,
          max_health: 0,
          move_speed: 0
        },
        sound: true,
        selected_skin: "default"
      };
    }

    function loadSave() {
      const fallback = defaultSave();

      try {
        const stored = JSON.parse(localStorage.getItem(SAVE_KEY));

        if (!stored) return fallback;

        fallback.best_score = Number(stored.best_score) || 0;
        fallback.coins = Number(stored.coins) || 0;
        fallback.sound = stored.sound !== false;
        fallback.selected_skin = stored.selected_skin || "default";

        if (stored.upgrades) {
          for (const key of Object.keys(fallback.upgrades)) {
            fallback.upgrades[key] = Number(stored.upgrades[key]) || 0;
          }
        }
      } catch (_) {}

      return fallback;
    }

    let saveData = loadSave();

    function saveGame() {
      try {
        localStorage.setItem(SAVE_KEY, JSON.stringify(saveData));
      } catch (_) {}
    }

    // ------------------------------------------------------------
    // Game state
    // ------------------------------------------------------------
    let state = "menu";
    let run = resetRun();

    let waveNum = 1;
    let waveState = "pause";
    let waveStart = now();
    let waveEnemies = [];
    let bossActive = false;
    let boss = null;

    let mapTheme = randomInt(0, MAPS.length - 1);
    let mapScroll = 0;
    let screenShake = 0;
    let waveBannerTime = 0;
    let particles = [];

    let shieldActive = false;
    let shieldStart = 0;

    let lastFrame = now();
    let frameScale = 1;

    const keys = {};
    const pointer = {
      x: 0,
      y: 0,
      clicked: false,
      down: false
    };

    function resetRun() {
      const maxHealth = 15 + saveData.upgrades.max_health;

      return {
        basket: {
          x: W / 2 - 40,
          y: H - 80,
          w: 80,
          h: 20
        },
        bullets: [],
        enemyBullets: [],
        score: 0,
        health: maxHealth,
        maxHealth,
        speed: 2,
        bulletSpeed: 8 + saveData.upgrades.bullet_speed * 2,
        fireCd: Math.max(60, 220 - saveData.upgrades.fire_rate * 20),
        lastFire: 0,
        coins: saveData.coins,
        shopOpen: false,
        runStart: now()
      };
    }

    function beginNewGame() {
      run = resetRun();

      waveNum = 1;
      waveState = "pause";
      waveStart = now();
      waveEnemies = [];
      bossActive = false;
      boss = null;
      particles = [];
      shieldActive = false;
      screenShake = 0;
      mapTheme = randomInt(0, MAPS.length - 1);

      startWave();
      state = "play";
    }

    // ------------------------------------------------------------
    // Entities
    // ------------------------------------------------------------
    function spawnEnemy() {
      const kind = weightedChoice();

      let color;
      let hp;
      let speed;
      let size;
      let score;
      let shootCd;

      if (kind === "fast") {
        color = ORANGE;
        hp = 1;
        speed = randomInt(3, 4);
        size = 16;
        score = 2;
        shootCd = 1100;
      } else if (kind === "tank") {
        color = PURPLE;
        hp = 2;
        speed = 1;
        size = 24;
        score = 3;
        shootCd = 900;
      } else {
        color = choose([GOLD, CYAN, PINK]);
        hp = 1;
        speed = 2;
        size = 20;
        score = 1;
        shootCd = 1300;
      }

      return {
        x: randomInt(10, W - size - 10),
        y: -size,
        w: size,
        h: size,
        delay: now() + WAVE_PAUSE_MS,
        color,
        hp,
        speed,
        score,
        kind,
        spawnTime: now(),
        lastShot: now(),
        shootCd
      };
    }

    function spawnBoss() {
      return {
        x: W / 2 - 45,
        y: -90,
        w: 90,
        h: 70,
        hp: 25,
        maxHp: 25,
        speed: 1,
        color: PURPLE,
        lastShot: 0,
        dir: 1
      };
    }

    function startWave() {
      if (waveNum % BOSS_EVERY === 0) {
        bossActive = true;
        boss = spawnBoss();
        waveEnemies = [];
      } else {
        bossActive = false;
        boss = null;
        waveEnemies = Array.from({ length: WAVE_SIZE }, spawnEnemy);
      }

      waveState = "pause";
      waveStart = now();
      waveBannerTime = now();
      mapTheme = randomInt(0, MAPS.length - 1);
    }

    function fireBullet() {
      const t = now();

      if (t - run.lastFire < run.fireCd) return;

      run.lastFire = t;
      run.bullets.push({
        x: run.basket.x + run.basket.w / 2 - 3,
        y: run.basket.y - 10,
        w: 6,
        h: 10
      });

      playSound("shoot");
    }

    function addExplosion(x, y, baseColor = GOLD, count = 22) {
      const colors = [baseColor, ORANGE, WHITE];

      for (let i = 0; i < count; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = 1.5 + Math.random() * 4;
        const life = randomInt(18, 40);

        particles.push({
          x,
          y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          life,
          maxLife: life,
          color: choose(colors),
          size: randomInt(2, 4)
        });
      }
    }

    function forceWaveLeave() {
      if (!waveEnemies.length) return;

      if (!shieldActive) {
        run.health -= waveEnemies.length;
      }

      for (const enemy of waveEnemies) {
        addExplosion(enemy.x + enemy.w / 2, enemy.y + enemy.h / 2, enemy.color, 10);
      }

      waveEnemies = [];
      screenShake = 12;
    }

    function hurtPlayer(amount = 1) {
      if (shieldActive) return;

      run.health -= amount;
      addExplosion(
        run.basket.x + run.basket.w / 2,
        run.basket.y + run.basket.h / 2,
        RED,
        14
      );
      playSound("hit");
    }

    function reward(score) {
      run.score += score;
      run.coins += score;
      saveData.coins = run.coins;
      saveData.best_score = Math.max(saveData.best_score, run.score);
      saveGame();
      playSound("coin");
    }

    function updateBoss(t) {
      if (!boss) return;

      boss.x += boss.dir * 2;

      if (boss.x < 20 || boss.x + boss.w > W - 20) {
        boss.dir *= -1;
      }

      if (boss.y < 60) {
        boss.y += 1;
      }

      if (t - boss.lastShot > 700) {
        boss.lastShot = t;
        run.enemyBullets.push({
          x: boss.x + boss.w / 2 - 3,
          y: boss.y + boss.h,
          w: 6,
          h: 12,
          speed: 6
        });
      }

      if (rectsOverlap(boss, run.basket)) {
        hurtPlayer(1);
      }
    }

    // ------------------------------------------------------------
    // Drawing helpers
    // ------------------------------------------------------------
    function drawText(text, x, y, color = WHITE, size = 28, align = "left") {
      ctx.fillStyle = color;
      ctx.font = `${size}px Arial, Helvetica, sans-serif`;
      ctx.textAlign = align;
      ctx.textBaseline = "top";
      ctx.fillText(String(text), x, y);
    }

    function roundedRect(x, y, w, h, radius = 16) {
      const r = Math.min(radius, w / 2, h / 2);

      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
    }

    function drawGlass(rect, fill = "255,255,255", border = "255,255,255", alpha = 160, borderWidth = 2, radius = 18) {
      roundedRect(rect.x, rect.y, rect.w, rect.h, radius);
      ctx.fillStyle = `rgba(${fill}, ${alpha / 255})`;
      ctx.fill();

      if (borderWidth > 0) {
        ctx.lineWidth = borderWidth;
        ctx.strokeStyle = `rgba(${border}, 0.7)`;
        ctx.stroke();
      }
    }

    function drawButton(rect, label, fill = "70,70,120", outline = "255,255,255", textColor = WHITE, fontSize = 28) {
      drawGlass(rect, fill, outline, 175, 2, 16);

      ctx.font = `${fontSize}px Arial, Helvetica, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = textColor;
      ctx.fillText(label, rect.x + rect.w / 2, rect.y + rect.h / 2 + 1);
    }

    function drawBackground() {
      const theme = MAPS[mapTheme];

      ctx.fillStyle = theme.bg;
      ctx.fillRect(0, 0, W, H);

      mapScroll = (mapScroll + 1) % W;

      for (let i = 0; i < 24; i++) {
        const x = (i * 87 + mapScroll) % W;
        const y = (i * 53 + Math.floor(mapScroll / 2)) % H;

        ctx.fillStyle = theme.stars;
        ctx.beginPath();
        ctx.arc(x, y, 1, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.fillStyle = theme.planet;
      ctx.beginPath();
      ctx.arc(W - 70, 100, 46, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = theme.accent;
      ctx.lineWidth = 2;

      ctx.beginPath();
      ctx.arc(80, 110, 26, 0, Math.PI * 2);
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(W / 2, 60, 16, 0, Math.PI * 2);
      ctx.stroke();
    }

    function drawParticles() {
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];

        p.x += p.vx * frameScale;
        p.y += p.vy * frameScale;
        p.vy += 0.06 * frameScale;
        p.life -= frameScale;

        if (p.life <= 0) {
          particles.splice(i, 1);
          continue;
        }

        const alpha = clamp(p.life / p.maxLife, 0, 1);

        ctx.globalAlpha = alpha;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, Math.max(1, p.size), 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }
    }

    function drawShip() {
      const t = now();
      const bob = Math.sin(t * 0.01) * 2;
      const x = run.basket.x;
      const y = H - 90 + bob;

      // Main triangular hull
      ctx.fillStyle = CYAN;
      ctx.beginPath();
      ctx.moveTo(x, y + 28);
      ctx.lineTo(x + 35, y - 20);
      ctx.lineTo(x + 70, y + 28);
      ctx.closePath();
      ctx.fill();

      // Body
      ctx.fillStyle = BROWN;
      ctx.fillRect(x, y, 70, 28);

      // Wings
      ctx.fillStyle = PINK;
      ctx.fillRect(x - 14, y + 8, 18, 10);
      ctx.fillRect(x + 66, y + 8, 18, 10);

      // Nose
      ctx.fillStyle = WHITE;
      ctx.fillRect(x + 26, y - 20, 18, 24);

      if (shieldActive) {
        const radius = 45 + Math.sin(t * 0.01) * 3;
        const centerX = run.basket.x + run.basket.w / 2;
        const centerY = run.basket.y + run.basket.h / 2;

        ctx.strokeStyle = CYAN;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.stroke();

        ctx.strokeStyle = WHITE;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius + 5, 0, Math.PI * 2);
        ctx.stroke();
      }
    }

    function drawHud(survive) {
      drawGlass({ x: 0, y: 0, w: W, h: 82 }, "10,12,24", "255,255,255", 85, 0, 0);

      drawText(`Score: ${run.score}`, 10, 10, WHITE, 28);
      drawText(`HP: ${run.health}/${run.maxHealth}`, 10, 64, WHITE, 22);
      drawText(`Best: ${saveData.best_score}`, 300, 10, WHITE, 28);
      drawText(`Coins: ${run.coins}`, 300, 34, WHITE, 28);
      drawText(`Time: ${survive}s`, 330, 64, WHITE, 22);

      drawText("Quests:", 160, 10, WHITE, 28);

      let y = 95;

      QUESTS.forEach(([name, goal], index) => {
        const progress = index < 3 ? run.score : survive;
        const done = progress >= goal;
        const marker = done ? "✓" : "-";

        drawText(
          `${marker} ${name}: ${Math.min(progress, goal)}/${goal}`,
          110,
          y,
          done ? GREEN : WHITE,
          22
        );

        y += 20;
      });
    }

    function drawWaveBanner() {
      const elapsed = now() - waveBannerTime;

      if (elapsed >= 1400) return;

      const alpha = clamp(1 - elapsed / 1400, 0, 1);

      ctx.fillStyle = `rgba(30, 40, 70, ${alpha * 0.5})`;
      roundedRect(60, 95, 360, 46, 16);
      ctx.fill();

      ctx.strokeStyle = `rgba(255,255,255,${alpha})`;
      ctx.lineWidth = 2;
      ctx.stroke();

      drawText(`WAVE ${waveNum}`, W / 2, 108, GOLD, 28, "center");
    }

    function drawControls() {
      const left = { x: 10, y: H - 90, w: 90, h: 70 };
      const right = { x: 105, y: H - 90, w: 90, h: 70 };
      const shoot = { x: W - 100, y: H - 90, w: 90, h: 70 };
      const shop = { x: W / 2 - 40, y: H - 90, w: 80, h: 28 };

      drawButton(left, "<", "70,70,110", "255,255,255", WHITE, 58);
      drawButton(right, ">", "70,70,110", "255,255,255", WHITE, 58);
      drawButton(shoot, "FIRE", "70,70,110", "255,255,255", WHITE, 24);
      drawButton(shop, "SHOP", "90,100,145", "255,255,255", WHITE, 16);

      return { left, right, shoot, shop };
    }

    function drawShopOverlay() {
      ctx.fillStyle = "rgba(5, 8, 18, 0.45)";
      ctx.fillRect(0, 0, W, H);

      const panel = { x: 32, y: 60, w: 416, h: 500 };
      drawGlass(panel, "40,52,90", "255,255,255", 165, 2, 18);

      drawText("SHOP", W / 2, 76, GOLD, 50, "center");
      drawText(`Coins: ${run.coins}`, W / 2, 125, WHITE, 28, "center");

      const buttons = [];
      let y = 170;

      for (const [label, cost, key] of SHOP_ITEMS) {
        const rect = { x: 52, y, w: 376, h: 54 };
        buttons.push({ rect, label, cost, key });

        const fill = run.coins >= cost ? "58,68,104" : "48,48,60";

        drawGlass(rect, fill, "255,255,255", 180, 2, 16);
        drawText(label, 68, y + 16, WHITE, 24);
        drawText(`${cost} coins`, 412, y + 16, GOLD, 24, "right");

        y += 74;
      }

      const back = { x: 165, y: 515, w: 150, h: 42 };
      drawButton(back, "BACK", "85,95,140", "255,255,255", WHITE, 24);

      return { buttons, back };
    }

    function drawBoss() {
      if (!boss) return;

      ctx.fillStyle = boss.color;
      roundedRect(boss.x, boss.y, boss.w, boss.h, 14);
      ctx.fill();

      ctx.strokeStyle = WHITE;
      ctx.lineWidth = 2;
      ctx.stroke();

      const healthWidth = 120 * boss.hp / boss.maxHp;

      ctx.fillStyle = RED;
      roundedRect(180, 140, 120, 10, 6);
      ctx.fill();

      ctx.fillStyle = GREEN;
      roundedRect(180, 140, healthWidth, 10, 6);
      ctx.fill();
    }

    function drawHealthBar() {
      const healthWidth = 150 * clamp(run.health / run.maxHealth, 0, 1);

      ctx.fillStyle = RED;
      roundedRect(10, 45, 150, 15, 8);
      ctx.fill();

      ctx.fillStyle = GREEN;
      roundedRect(10, 45, healthWidth, 15, 8);
      ctx.fill();
    }

    // ------------------------------------------------------------
    // Shop
    // ------------------------------------------------------------
    function handleShopPurchase(key, cost) {
      if (run.coins < cost) return;

      run.coins -= cost;
      saveData.coins = run.coins;

      if (key === "shield") {
        shieldActive = true;
        shieldStart = now();
        playSound("upgrade");
        saveGame();
        return;
      }

      saveData.upgrades[key] += 1;

      if (key === "bullet_speed") {
        run.bulletSpeed += 2;
      } else if (key === "fire_rate") {
        run.fireCd = Math.max(60, run.fireCd - 20);
      } else if (key === "max_health") {
        run.maxHealth += 1;
        run.health += 1;
      }

      playSound("upgrade");
      saveGame();
    }

    function handleShopClick(shop) {
      for (const item of shop.buttons) {
        if (pointInRect(pointer.x, pointer.y, item.rect)) {
          handleShopPurchase(item.key, item.cost);
          return;
        }
      }

      if (pointInRect(pointer.x, pointer.y, shop.back)) {
        if (state === "shop") {
          state = "menu";
        } else {
          run.shopOpen = false;
        }
      }
    }

    // ------------------------------------------------------------
    // Input
    // ------------------------------------------------------------
    function getCanvasPoint(event) {
      const rect = canvas.getBoundingClientRect();

      return {
        x: (event.clientX - rect.left) * (W / rect.width),
        y: (event.clientY - rect.top) * (H / rect.height)
      };
    }

    canvas.addEventListener("pointerdown", (event) => {
      event.preventDefault();

      const p = getCanvasPoint(event);
      pointer.x = p.x;
      pointer.y = p.y;
      pointer.clicked = true;
      pointer.down = true;

      try {
        canvas.setPointerCapture(event.pointerId);
      } catch (_) {}
    });

    canvas.addEventListener("pointermove", (event) => {
      const p = getCanvasPoint(event);
      pointer.x = p.x;
      pointer.y = p.y;
    });

    canvas.addEventListener("pointerup", () => {
      pointer.down = false;
    });

    canvas.addEventListener("pointercancel", () => {
      pointer.down = false;
    });

    window.addEventListener("keydown", (event) => {
      keys[event.key] = true;

      if (["ArrowLeft", "ArrowRight", " ", "Spacebar"].includes(event.key)) {
        event.preventDefault();
      }

      if (state === "play") {
        if (event.key === " " || event.key === "Spacebar") {
          fireBullet();
        }

        if (event.key === "s" || event.key === "S" || event.key === "/") {
          run.shopOpen = !run.shopOpen;
        }

        // Debug bonus: Shift + =
        if (event.key === "=" && event.shiftKey) {
          run.coins += 100;
          saveData.coins = run.coins;
          playSound("coin");
          saveGame();
        }
      }
    });

    window.addEventListener("keyup", (event) => {
      keys[event.key] = false;
    });

    function controllerMove() {
      let left = false;
      let right = false;
      let shoot = false;

      const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];

      for (const pad of gamepads) {
        if (!pad) continue;

        const axis = pad.axes?.[0] ?? 0;

        if (axis < -0.4) left = true;
        if (axis > 0.4) right = true;
        if (pad.buttons?.[0]?.pressed) shoot = true;
      }

      return { left, right, shoot };
    }

    // ------------------------------------------------------------
    // State screens
    // ------------------------------------------------------------
    function drawMenu() {
      ctx.fillStyle = BLUE;
      ctx.fillRect(0, 0, W, H);

      const play = { x: 160, y: 220, w: 160, h: 48 };
      const shop = { x: 160, y: 285, w: 160, h: 48 };
      const quit = { x: 160, y: 350, w: 160, h: 48 };

      drawText("STAR MISSION", W / 2, 80, GOLD, 48, "center");
      drawText("Mobile + controller friendly", W / 2, 140, WHITE, 22, "center");

      drawButton(play, "PLAY");
      drawButton(shop, "SHOP");
      drawButton(quit, "QUIT");

      drawText(
        `Best: ${saveData.best_score}  Coins: ${saveData.coins}`,
        W / 2,
        430,
        WHITE,
        26,
        "center"
      );

      if (pointer.clicked) {
        if (pointInRect(pointer.x, pointer.y, play)) {
          beginNewGame();
        } else if (pointInRect(pointer.x, pointer.y, shop)) {
          run = resetRun();
          state = "shop";
        } else if (pointInRect(pointer.x, pointer.y, quit)) {
          saveGame();
          drawText("You may close this browser tab.", W / 2, 510, GOLD, 20, "center");
        }
      }
    }

    function drawEndScreen(success) {
      ctx.fillStyle = success ? "#0a2810" : "#2d0c0c";
      ctx.fillRect(0, 0, W, H);

      const title = success ? "MISSION SUCCESS" : "YOU LOSE";
      const againLabel = success ? "PLAY AGAIN" : "RESTART";
      const fill = success ? "70,110,80" : "120,70,70";

      const again = { x: 145, y: 300, w: 190, h: 48 };
      const menu = { x: 145, y: 372, w: 190, h: 48 };

      drawText(title, W / 2, 135, WHITE, success ? 46 : 54, "center");
      drawText(`Score: ${run.score}`, W / 2, 215, WHITE, 28, "center");

      drawButton(again, againLabel, fill);
      drawButton(menu, "MAIN MENU", fill);

      if (pointer.clicked) {
        if (pointInRect(pointer.x, pointer.y, again)) {
          beginNewGame();
        } else if (pointInRect(pointer.x, pointer.y, menu)) {
          state = "menu";
        }
      }
    }

    // ------------------------------------------------------------
    // Gameplay update
    // ------------------------------------------------------------
    function updatePlay() {
      const t = now();
      const survive = Math.floor((t - run.runStart) / 1000);

      const controller = controllerMove();
      const movement = 6 + saveData.upgrades.move_speed;

      if ((keys.ArrowLeft || controller.left) && run.basket.x > 0) {
        run.basket.x -= movement * frameScale;
      }

      if ((keys.ArrowRight || controller.right) && run.basket.x + run.basket.w < W) {
        run.basket.x += movement * frameScale;
      }

      run.basket.x = clamp(run.basket.x, 0, W - run.basket.w);

      if (controller.shoot) {
        fireBullet();
      }

      const controls = drawControls();

      if (pointer.clicked && !run.shopOpen) {
        if (pointInRect(pointer.x, pointer.y, controls.left)) {
          run.basket.x = Math.max(0, run.basket.x - movement);
        } else if (pointInRect(pointer.x, pointer.y, controls.right)) {
          run.basket.x = Math.min(W - run.basket.w, run.basket.x + movement);
        } else if (pointInRect(pointer.x, pointer.y, controls.shoot)) {
          fireBullet();
        } else if (pointInRect(pointer.x, pointer.y, controls.shop)) {
          run.shopOpen = true;
        }
      }

      if (shieldActive && t - shieldStart >= SHIELD_DURATION) {
        shieldActive = false;
      }

      if (!waveEnemies.length && !bossActive && waveState !== "active") {
        startWave();
      }

      if (waveState === "pause") {
        if (t - waveStart >= WAVE_PAUSE_MS) {
          waveState = "active";
          waveStart = t;
        }
      } else if (waveState === "active") {
        updateActiveWave(t);
      }

      updateBullets();
      drawGameWorld(survive);

      if (run.shopOpen) {
        const shop = drawShopOverlay();

        if (pointer.clicked) {
          handleShopClick(shop);
        }
      }

      if (run.score >= 25 || survive >= 300) {
        saveData.coins = run.coins;
        saveGame();
        state = "success";
      } else if (run.health <= 0) {
        saveData.coins = run.coins;
        saveGame();
        state = "lose";
      }
    }

    function updateActiveWave(t) {
      if (bossActive && boss) {
        updateBoss(t);

        for (let i = run.bullets.length - 1; i >= 0; i--) {
          const bullet = run.bullets[i];

          if (rectsOverlap(bullet, boss)) {
            run.bullets.splice(i, 1);
            boss.hp -= 1;

            addExplosion(bullet.x + bullet.w / 2, bullet.y + bullet.h / 2, CYAN, 6);
            playSound("hit");

            if (boss.hp <= 0) {
              addExplosion(boss.x + boss.w / 2, boss.y + boss.h / 2, GOLD, 40);
              playSound("boom");

              reward(20);

              bossActive = false;
              boss = null;
              waveNum += 1;
              waveState = "pause";
              waveStart = t;
              startWave();
            }

            break;
          }
        }
      } else {
        for (let enemyIndex = waveEnemies.length - 1; enemyIndex >= 0; enemyIndex--) {
          const enemy = waveEnemies[enemyIndex];

          if (t >= enemy.delay) {
            enemy.y += enemy.speed * frameScale;
          }

          if (t - enemy.lastShot >= enemy.shootCd && t >= enemy.delay) {
            enemy.lastShot = t;

            run.enemyBullets.push({
              x: enemy.x + enemy.w / 2 - 3,
              y: enemy.y + enemy.h,
              w: 5,
              h: 10,
              speed: randomInt(4, 6)
            });
          }

          if (enemy.y > H) {
            if (!shieldActive) {
              run.health -= 1;
            }

            addExplosion(enemy.x + enemy.w / 2, enemy.y + enemy.h / 2, RED, 10);
            playSound("hit");
            waveEnemies.splice(enemyIndex, 1);
            continue;
          }

          if (rectsOverlap(enemy, run.basket)) {
            if (!shieldActive) {
              run.health -= 1;
            }

            addExplosion(enemy.x + enemy.w / 2, enemy.y + enemy.h / 2, RED, 10);
            playSound("hit");
            waveEnemies.splice(enemyIndex, 1);
            continue;
          }

          for (let bulletIndex = run.bullets.length - 1; bulletIndex >= 0; bulletIndex--) {
            const bullet = run.bullets[bulletIndex];

            if (!rectsOverlap(bullet, enemy)) continue;

            run.bullets.splice(bulletIndex, 1);
            enemy.hp -= 1;

            addExplosion(
              bullet.x + bullet.w / 2,
              bullet.y + bullet.h / 2,
              enemy.color,
              8
            );

            playSound("hit");

            if (enemy.hp <= 0) {
              waveEnemies.splice(enemyIndex, 1);
              reward(enemy.score);
              screenShake = 10;
            }

            break;
          }
        }

        if (!waveEnemies.length) {
          waveNum += 1;
          waveState = "pause";
          waveStart = t;
          startWave();
        } else if (t - waveStart >= WAVE_PAUSE_MS + WAVE_ACTIVE_MS) {
          forceWaveLeave();
          waveNum += 1;
          waveState = "pause";
          waveStart = t;
          startWave();
        }
      }
    }

    function updateBullets() {
      for (let i = run.bullets.length - 1; i >= 0; i--) {
        const bullet = run.bullets[i];
        bullet.y -= run.bulletSpeed * frameScale;

        if (bullet.y + bullet.h < 0) {
          run.bullets.splice(i, 1);
        }
      }

      for (let i = run.enemyBullets.length - 1; i >= 0; i--) {
        const bullet = run.enemyBullets[i];
        bullet.y += bullet.speed * frameScale;

        if (bullet.y > H) {
          run.enemyBullets.splice(i, 1);
          continue;
        }

        if (rectsOverlap(bullet, run.basket)) {
          run.enemyBullets.splice(i, 1);
          hurtPlayer(1);
        }
      }
    }

    function drawGameWorld(survive) {
      drawBackground();

      let offsetX = 0;
      let offsetY = 0;

      if (screenShake > 0) {
        offsetX = randomInt(-screenShake, screenShake);
        offsetY = randomInt(-screenShake, screenShake);
        screenShake -= 1;
      }

      ctx.save();
      ctx.translate(offsetX, offsetY);

      drawShip();

      for (const enemy of waveEnemies) {
        const pulseRadius = Math.max(
          2,
          enemy.w / 2 + Math.sin(now() * 0.01 + enemy.x) * 2
        );

        ctx.fillStyle = enemy.color;
        ctx.beginPath();
        ctx.arc(enemy.x + enemy.w / 2, enemy.y + enemy.h / 2, pulseRadius, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = WHITE;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(enemy.x + enemy.w / 2, enemy.y + enemy.h / 2, pulseRadius, 0, Math.PI * 2);
        ctx.stroke();
      }

      drawBoss();

      for (const bullet of run.enemyBullets) {
        ctx.fillStyle = ORANGE;
        roundedRect(bullet.x, bullet.y, bullet.w, bullet.h, 2);
        ctx.fill();
      }

      for (const bullet of run.bullets) {
        ctx.fillStyle = WHITE;
        roundedRect(bullet.x, bullet.y, bullet.w, bullet.h, 2);
        ctx.fill();
      }

      drawParticles();

      ctx.restore();

      drawHud(survive);
      drawWaveBanner();
      drawHealthBar();
    }

    // ------------------------------------------------------------
    // Main loop
    // ------------------------------------------------------------
    function gameLoop(timestamp) {
      const delta = timestamp - lastFrame;
      lastFrame = timestamp;
      frameScale = clamp(delta / (1000 / 60), 0.3, 2.2);

      ctx.clearRect(0, 0, W, H);

      if (state === "menu") {
        drawMenu();
      } else if (state === "shop") {
        ctx.fillStyle = BLUE;
        ctx.fillRect(0, 0, W, H);

        const shop = drawShopOverlay();

        if (pointer.clicked) {
          handleShopClick(shop);
        }
      } else if (state === "play") {
        updatePlay();
      } else if (state === "lose") {
        drawEndScreen(false);
      } else if (state === "success") {
        drawEndScreen(true);
      }

      pointer.clicked = false;
      requestAnimationFrame(gameLoop);
    }

    window.addEventListener("beforeunload", () => {
      if (run) {
        saveData.coins = run.coins;
      }

      saveGame();
    });

    requestAnimationFrame(gameLoop);
  </script>
</body>
</html>
