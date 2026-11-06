const DATA_URL = "api/data/janova";
const WEB4SPORT_URL = "api/data/web4sport";
let dataSource = "janova";
const REFRESH_MS = 250;
const TEAM_POINT_HIGHLIGHT_MS = 6000;

const scenes = {
  neutral: document.getElementById("neutralScene"),
  summary: document.getElementById("summaryScene"),
  live: document.getElementById("liveScene")
};

let currentScene = "neutral";
let previousValues = new Map();
let previousTeamScore = null;
let previousGameKey = null;
let highlightUntil = 0;
let highlightTimer = null;
let latestRenderState = null;

function score2(value) {
  return String(Math.max(0, Number(value) || 0)).padStart(2, "0");
}

// V2.9.1: competition.json wird von der UNO Bridge v0.4.2 bereitgestellt.
// Nur bei identischer Spiel-ID und Quelle verwenden, damit keine alte Liga stehen bleibt.
let publishedCompetition = null;
async function refreshCompetition() {
  try {
    const response = await fetch(`competition.json?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    publishedCompetition = data?.gameId && data?.competition ? data : null;
  } catch (error) {
    publishedCompetition = null;
  }
  if (latestRenderState?.contextBoard) {
    fillMatchHeader(latestRenderState.contextBoard);
  }
}
refreshCompetition();
setInterval(refreshCompetition, 2000);

function competitionText(board) {
  const source = String(board?.game?.source || "");
  const gameId = String(board?.game?.id || "");
  if (publishedCompetition && publishedCompetition.source === source &&
      publishedCompetition.gameId === gameId) {
    return publishedCompetition.competition;
  }
  if (source === "web4sport") return "STADTOBERLIGA";
  if (source === "janova") return "FREUNDSCHAFTSSPIEL";
  if (source === "ttlive") return "LIGA WIRD ERMITTELT";
  return "TISCHTENNIS";
}

function chooseGameGroup(boards) {
  const active = boards.filter(
    b => b?.active && b?.game?.id && b?.match?.state === "InProgress"
  );

  if (!active.length) return [];

  const groups = new Map();
  for (const board of active) {
    const key = `${board.game.source || ""}:${board.game.id}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(board);
  }

  return [...groups.values()].sort((a, b) => b.length - a.length)[0];
}

function findRememberedGame(boards) {
  return boards.find(b => b?.hasGame && b?.game?.id && b?.teamScore) || null;
}

function gameKey(board) {
  return board?.game?.id ? `${board.game.source || ""}:${board.game.id}` : null;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el && el.textContent !== String(value)) el.textContent = String(value);
}

function flashChanged(el, value, key) {
  if (!el) return;
  const number = Number(value ?? 0);
  const old = previousValues.get(key);

  if (el.textContent !== String(number)) el.textContent = String(number);

  if (old !== undefined && old !== number) {
    el.classList.remove("changed");
    void el.offsetWidth;
    el.classList.add("changed");
    clearTimeout(el._changedTimer);
    el._changedTimer = setTimeout(() => el.classList.remove("changed"), 700);
  }

  previousValues.set(key, number);
}


function fitSingleLine(el, minPx = 18) {
  if (!el) return;

  // Erst immer auf die CSS-Ausgangsgröße zurücksetzen.
  el.style.fontSize = "";

  const computed = getComputedStyle(el);
  let size = parseFloat(computed.fontSize) || minPx;

  // Solange verkleinern, bis der komplette Text ohne Ellipse hineinpasst.
  while (el.scrollWidth > el.clientWidth + 1 && size > minPx) {
    size -= 1;
    el.style.fontSize = `${size}px`;
  }
}

function fitHeaderNames() {
  fitSingleLine(document.getElementById("homeTeam"), 22);
  fitSingleLine(document.getElementById("awayTeam"), 22);
  fitSingleLine(document.getElementById("summaryHomeTeam"), 24);
  fitSingleLine(document.getElementById("summaryAwayTeam"), 24);
}

function fitPlayerNames(card) {
  if (!card) return;
  for (const el of card.querySelectorAll(".player-name")) {
    fitSingleLine(el, 17);
  }
}

function fillMatchHeader(board) {
  const home = board?.teams?.home || "HEIM";
  const away = board?.teams?.away || "GAST";
  const homeTotal = score2(board?.teamScore?.home);
  const awayTotal = score2(board?.teamScore?.away);
  const competition = competitionText(board);
  const twoDigits = Math.max(Number(board?.teamScore?.home || 0), Number(board?.teamScore?.away || 0)) >= 10;
  for (const id of ['homeTotal', 'awayTotal', 'summaryHomeTotal', 'summaryAwayTotal']) {
    document.getElementById(id)?.classList.toggle('two-digit-total', twoDigits);
  }

  setText("homeTeam", home);
  setText("awayTeam", away);
  const key = gameKey(board) || "game";
  flashChanged(document.getElementById("homeTotal"), Number(board?.teamScore?.home || 0), `${key}-team-home-header`);
  flashChanged(document.getElementById("awayTotal"), Number(board?.teamScore?.away || 0), `${key}-team-away-header`);
  setText("competitionLabel", competition);

  setText("summaryHomeTeam", home);
  setText("summaryAwayTeam", away);
  flashChanged(document.getElementById("summaryHomeTotal"), Number(board?.teamScore?.home || 0), `${key}-team-home-summary`);
  flashChanged(document.getElementById("summaryAwayTotal"), Number(board?.teamScore?.away || 0), `${key}-team-away-summary`);
  setText("summaryCompetition", competition);

  requestAnimationFrame(fitHeaderNames);
}

function switchScene(next, options = {}) {
  const { pointHighlight = false } = options;

  for (const [name, scene] of Object.entries(scenes)) {
    const visible = name === next;
    scene.classList.toggle("is-visible", visible);
    scene.setAttribute("aria-hidden", visible ? "false" : "true");
  }

  const summary = scenes.summary;
  summary.classList.toggle("point-highlight", next === "summary" && pointHighlight);

  if (currentScene !== next) {
    currentScene = next;
  }
}

function detectTeamPoint(contextBoard) {
  const key = gameKey(contextBoard);
  const score = {
    home: Number(contextBoard?.teamScore?.home || 0),
    away: Number(contextBoard?.teamScore?.away || 0)
  };

  // Neue Mannschaftspartie: nur Basiswert merken, niemals beim ersten Poll jubeln.
  if (!previousTeamScore || previousGameKey !== key) {
    previousTeamScore = score;
    previousGameKey = key;
    return false;
  }

  const pointFell =
    score.home > previousTeamScore.home ||
    score.away > previousTeamScore.away;

  previousTeamScore = score;
  previousGameKey = key;
  return pointFell;
}

function startTeamPointHighlight() {
  highlightUntil = Date.now() + TEAM_POINT_HIGHLIGHT_MS;
  document.getElementById("pointCall").classList.add("show");

  if (highlightTimer) clearTimeout(highlightTimer);
  highlightTimer = setTimeout(() => {
    highlightUntil = 0;
    document.getElementById("pointCall").classList.remove("show");
    if (latestRenderState) applyScene(latestRenderState);
  }, TEAM_POINT_HIGHLIGHT_MS);
}

function playerNames(side) {
  const players = Array.isArray(side?.players) && side.players.length
    ? side.players
    : ["?"];
  return players;
}

function ballSituation(board) {
  const homePoints = Number(board?.sideOne?.points ?? 0);
  const awayPoints = Number(board?.sideTwo?.points ?? 0);
  const homeSets = Number(board?.sideOne?.sets ?? 0);
  const awaySets = Number(board?.sideTwo?.sets ?? 0);

  // Sobald der aktuelle Satz bereits gewonnen ist, gibt es keinen Satz-/Matchball mehr.
  // Tischtennis: ab 11 Punkten mit mindestens 2 Punkten Vorsprung ist der Satz beendet.
  const setIsFinished =
    (homePoints >= 11 && homePoints - awayPoints >= 2) ||
    (awayPoints >= 11 && awayPoints - homePoints >= 2);
  if (setIsFinished) return null;

  // Falls Firestore den Matchstatus bereits umgestellt hat, ebenfalls nichts mehr anzeigen.
  if (board?.match?.state && board.match.state !== "InProgress") return null;

  let side = null;
  if (homePoints >= 10 && homePoints - awayPoints >= 1) side = "home";
  if (awayPoints >= 10 && awayPoints - homePoints >= 1) side = "away";
  if (!side) return null;

  const sets = side === "home" ? homeSets : awaySets;
  const team = side === "home"
    ? (board?.teams?.home || "HEIM")
    : (board?.teams?.away || "GAST");
  const type = sets >= 2 ? "MATCHBALL" : "SATZBALL";

  return { side, type, team };
}

function updateBallCall(card, board) {
  const call = card.querySelector(".ball-call");
  if (!call) return;

  const situation = ballSituation(board);
  if (!situation) {
    call.classList.remove("show", "matchball", "home", "away", "ball-enter");
    call.dataset.signature = "";
    call.setAttribute("aria-hidden", "true");
    return;
  }

  const signature = `${situation.type}|${situation.side}|${situation.team}`;
  call.querySelector(".ball-kind").textContent = situation.type;
  call.querySelector(".ball-team").textContent = situation.team;
  call.classList.toggle("matchball", situation.type === "MATCHBALL");
  call.classList.toggle("home", situation.side === "home");
  call.classList.toggle("away", situation.side === "away");
  call.classList.add("show");
  call.setAttribute("aria-hidden", "false");

  // Nur beim Entstehen oder Wechsel der Ball-Situation animieren.
  if (call.dataset.signature !== signature) {
    call.dataset.signature = signature;
    call.classList.remove("ball-enter");
    void call.offsetWidth;
    call.classList.add("ball-enter");
    clearTimeout(call._ballTimer);
    call._ballTimer = setTimeout(() => call.classList.remove("ball-enter"), 1100);
  }
}

function createCard(board) {
  const card = document.createElement("article");
  card.className = "game-card card-enter";
  card.dataset.matchId = board.match?.id || `slot-${board.slot}`;

  card.innerHTML = `
    <div class="card-head">
      <span class="table-label"></span>
      <span class="type-label"></span>
    </div>
    <div class="side home-side">
      <div class="player-block home-players"></div>
      <div class="numbers">
        <div class="metric"><span class="metric-label">SÄTZE</span><span class="sets home-sets"></span></div>
        <div class="metric"><span class="metric-label">PUNKTE</span><span class="points home-points"></span></div>
      </div>
    </div>
    <div class="vs-line"></div>
    <div class="side away-side">
      <div class="player-block away-players"></div>
      <div class="numbers">
        <div class="metric"><span class="metric-label">SÄTZE</span><span class="sets away-sets"></span></div>
        <div class="metric"><span class="metric-label">PUNKTE</span><span class="points away-points"></span></div>
      </div>
    </div>
    <div class="ball-call" aria-hidden="true">
      <span class="ball-kind"></span>
      <span class="ball-team"></span>
    </div>`;

  requestAnimationFrame(() => card.classList.remove("card-enter"));
  updateCard(card, board);
  return card;
}

function updatePlayers(block, side) {
  const players = playerNames(side);
  const signature = players.join("|") + `|${Boolean(side?.serving)}`;
  if (block.dataset.signature === signature) return;
  block.dataset.signature = signature;
  block.classList.toggle("players-double", players.length > 1);
  block.innerHTML = players.map(name => {
    const div = document.createElement("div");
    div.className = "player-name";
    div.textContent = name;
    return div.outerHTML;
  }).join("") + `
    <div class="serve ${side?.serving ? "" : "hidden"}">
      <span class="serve-dot"></span>AUFSCHLAG
    </div>`;
}

function updateMetric(el, value, key) {
  flashChanged(el, value, key);
}

function updateCard(card, board) {
  const id = board.match?.id || `slot-${board.slot}`;
  card.dataset.matchId = id;
  card.querySelector(".table-label").textContent = board.game?.source === "web4sport" ? `SPIEL ${board.slot}` : `TISCH ${board.slot}`;
  card.querySelector(".type-label").textContent = board.match?.type === "Double" ? "DOPPEL" : "EINZEL";

  updatePlayers(card.querySelector(".home-players"), board.sideOne || {});
  updatePlayers(card.querySelector(".away-players"), board.sideTwo || {});

  updateMetric(card.querySelector(".home-sets"), board.sideOne?.sets, `${id}-home-sets`);
  updateMetric(card.querySelector(".away-sets"), board.sideTwo?.sets, `${id}-away-sets`);
  updateMetric(card.querySelector(".home-points"), board.sideOne?.points, `${id}-home-points`);
  updateMetric(card.querySelector(".away-points"), board.sideTwo?.points, `${id}-away-points`);
  updateBallCall(card, board);
  requestAnimationFrame(() => fitPlayerNames(card));
}

function snapshotPositions(container) {
  const map = new Map();
  for (const card of container.querySelectorAll(".game-card")) {
    map.set(card.dataset.matchId, card.getBoundingClientRect());
  }
  return map;
}

function animateReflow(container, before) {
  for (const card of container.querySelectorAll(".game-card")) {
    const old = before.get(card.dataset.matchId);
    if (!old) continue;
    const now = card.getBoundingClientRect();
    const dx = old.left - now.left;
    const dy = old.top - now.top;
    const sx = old.width / Math.max(now.width, 1);
    const sy = old.height / Math.max(now.height, 1);

    if (Math.abs(dx) < 1 && Math.abs(dy) < 1 && Math.abs(sx - 1) < .01 && Math.abs(sy - 1) < .01) continue;

    card.animate([
      { transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`, transformOrigin: "top left" },
      { transform: "translate(0,0) scale(1,1)", transformOrigin: "top left" }
    ], {
      duration: 460,
      easing: "cubic-bezier(.22,.75,.22,1)"
    });
  }
}

function renderLiveCards(active) {
  const games = document.getElementById("games");
  const sorted = [...active].sort((a, b) => a.slot - b.slot).slice(0, 3);
  const before = snapshotPositions(games);
  const wanted = new Set(sorted.map(b => b.match?.id || `slot-${b.slot}`));

  for (const card of [...games.querySelectorAll(".game-card")]) {
    if (!wanted.has(card.dataset.matchId)) {
      card.classList.add("card-leave");
      setTimeout(() => card.remove(), 260);
    }
  }

  for (const board of sorted) {
    const id = board.match?.id || `slot-${board.slot}`;
    let card = [...games.querySelectorAll(".game-card")]
      .find(el => el.dataset.matchId === id);
    if (!card) {
      card = createCard(board);
      games.appendChild(card);
    } else {
      updateCard(card, board);
      games.appendChild(card); // hält Reihenfolge stabil nach Slot
    }
  }

  games.className = `games count-${Math.max(1, Math.min(sorted.length, 3))}`;
  requestAnimationFrame(() => animateReflow(games, before));
}

let scoreboardMode = localStorage.getItem("scoreboardV2Mode") === "total" ? "total" : "full";

function applyScene(state) {
  // V2.9: Im Ergebnis-Modus wird bei erkannter Partie immer nur der Gesamtstand gezeigt.
  if (scoreboardMode === "total") {
    if (!state.contextBoard) {
      switchScene("neutral");
      return;
    }
    fillMatchHeader(state.contextBoard);
    switchScene("summary", { pointHighlight: false });
    return;
  }
  // Mannschaftspunkt hat Vorrang vor allen normalen Zuständen.
  if (Date.now() < highlightUntil && state.contextBoard) {
    fillMatchHeader(state.contextBoard);
    switchScene("summary", { pointHighlight: true });
    return;
  }

  // 1. Noch keine Partie erkannt: nur Hintergrund/Rahmen/Logo.
  if (!state.contextBoard) {
    switchScene("neutral");
    return;
  }

  fillMatchHeader(state.contextBoard);

  // 2. Partie erkannt, aber kein InProgress-Spiel: Gesamtstand.
  if (!state.active.length) {
    switchScene("summary", { pointHighlight: false });
    return;
  }

  // 3. 1–3 aktive Spiele: Live-Regie.
  renderLiveCards(state.active);
  switchScene("live");
}

function render(data) {
  const boards = Array.isArray(data?.scoreboards) ? data.scoreboards : [];
  const activeGroup = chooseGameGroup(boards);
  const contextBoard = activeGroup[0] || findRememberedGame(boards);
  const active = activeGroup.slice().sort((a, b) => a.slot - b.slot);

  const state = { boards, active, contextBoard };
  latestRenderState = state;

  if (contextBoard) {
    fillMatchHeader(contextBoard);
    if (detectTeamPoint(contextBoard)) {
      startTeamPointHighlight();
    }
  } else {
    previousTeamScore = null;
    previousGameKey = null;
  }

  applyScene(state);

  const badge = document.getElementById("statusBadge");
  if (!contextBoard) {
    badge.textContent = `BEREIT · ${new Date().toLocaleTimeString("de-DE")}`;
    badge.classList.add("ok");
  } else {
    badge.textContent = `LIVE · ${new Date().toLocaleTimeString("de-DE")} · ${active.length} SPIEL${active.length === 1 ? "" : "E"}`;
    badge.classList.add("ok");
  }
}

async function refresh() {
  const badge = document.getElementById("statusBadge");

  try {
    const requestedSource = dataSource;
    const url = requestedSource === "web4sport" ? WEB4SPORT_URL : DATA_URL;
    const response = await fetch(`${url}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const raw = await response.json();
    if (requestedSource !== dataSource) return;
    if (window.v2DataState && window.v2DataState(raw)) return;
    if (dataSource === "web4sport") {
      const age = Date.now() - Date.parse(raw.updated || "");
      if (!Number.isFinite(age) || age > 90000 || age < -30000) {
        throw new Error("Web4Sport-Daten veraltet oder Reader gestoppt");
      }
      render(convertWeb4Sport(raw));
    } else {
      render(raw);
    }
  } catch (error) {
    badge.textContent = `Datenfehler: ${error.message}`;
    badge.classList.remove("ok");
  }
}

window.addEventListener("resize", () => {
  requestAnimationFrame(() => {
    fitHeaderNames();
    document.querySelectorAll(".game-card").forEach(fitPlayerNames);
  });
});

refresh();
setInterval(refresh, REFRESH_MS);


// =========================================================
// V2.4 – Sponsorleiste + lokale Uhr
// =========================================================
(function initScoreFooter() {
  function mount() {
    if (document.querySelector('.score-footer')) return;

    const arena = document.querySelector('.arena') || document.body;
    const footer = document.createElement('footer');
    footer.className = 'score-footer';
    footer.innerHTML = `
      <div class="sponsor-strip">
        <div class="sponsor-tagline" id="clubWebsite"></div>
      </div>
      <div class="score-clock" aria-label="Aktuelle Uhrzeit">
        <div class="score-clock-time" id="scoreClockTime">--:--</div>
        <div class="score-clock-date" id="scoreClockDate"></div>
      </div>`;
    arena.appendChild(footer);

    const timeEl = footer.querySelector('#scoreClockTime');
    const dateEl = footer.querySelector('#scoreClockDate');

    const updateClock = () => {
      const now = new Date();
      timeEl.textContent = new Intl.DateTimeFormat('de-DE', {
        hour: '2-digit', minute: '2-digit', hour12: false
      }).format(now);
      dateEl.textContent = new Intl.DateTimeFormat('de-DE', {
        day: '2-digit', month: '2-digit', year: 'numeric'
      }).format(now);
    };
    updateClock();
    setInterval(updateClock, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();


// V2.4.1 – erste Ziffer des Gesamtstands oben rot hinterlegen
(function markHomeTotalScore() {
  function mark() {
    // Bevorzugt vorhandene .total-Elemente; erstes Element ist Heim.
    const totals = document.querySelectorAll('.total');
    if (totals.length >= 2) {
      totals[0].classList.add('total-home-highlight');
      return;
    }

    // Falls beide Werte in einem Container liegen, erstes direktes Zahlenkind markieren.
    const score = document.querySelector('.total-score, .match-score, .overall-score');
    if (score) {
      const candidates = [...score.children].filter(el =>
        el.textContent.trim().match(/^\d+$/)
      );
      if (candidates.length) candidates[0].classList.add('total-home-highlight');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mark);
  } else {
    mark();
  }
})();


// V2.5 – Gast-Gesamtstand als dunkles Gegenstück markieren
(function markAwayTotalScore() {
  function mark() {
    const totals = document.querySelectorAll('.total');
    if (totals.length >= 2) {
      totals[0].classList.add('total-home-highlight');
      totals[1].classList.add('total-away-highlight');
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mark);
  } else {
    mark();
  }
})();


// =========================================================
// V2.7 – Theme Engine
// =========================================================
function hexToRgbTuple(hex) {
  const h = String(hex || "").replace("#","");
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return "9,11,14";
  return `${parseInt(h.slice(0,2),16)},${parseInt(h.slice(2,4),16)},${parseInt(h.slice(4,6),16)}`;
}

function applyTheme(theme) {
  const root = document.documentElement;
  const arena = document.querySelector(".arena");
  const c = theme.colors || {};
  root.style.setProperty("--theme-primary", c.primary || "#f10d1d");
  root.style.setProperty("--theme-primary-dark", c.primaryDark || "#850008");
  root.style.setProperty("--theme-accent", c.accent || c.primary || "#f10d1d");
  root.style.setProperty("--theme-border", c.border || c.primary || "#f10d1d");
  root.style.setProperty("--theme-text", c.text || "#fff");
  root.style.setProperty("--theme-score-tile", c.scoreTile || c.primary || "#f10d1d");
  root.style.setProperty("--theme-score-tile-dark", c.scoreTileDark || c.primaryDark || "#850008");
  root.style.setProperty("--theme-header-start", c.headerStart || c.primary || "#f10d1d");
  root.style.setProperty("--theme-header-end", c.headerEnd || c.primaryDark || "#850008");
  root.style.setProperty("--theme-serve", c.serve || "#fff");
  root.style.setProperty("--theme-footer", c.footer || "#fff");
  root.style.setProperty("--theme-bg-tint-rgb", hexToRgbTuple(c.backgroundTint || "#000000"));
  root.style.setProperty("--theme-card-rgb", hexToRgbTuple(c.card || "#090b0e"));
  root.style.setProperty("--card-opacity", String(theme.cardOpacity ?? .80));

  // Backward-compatible variables used by existing CSS
  root.style.setProperty("--red", c.primary || "#f10d1d");
  root.style.setProperty("--red2", c.primaryDark || "#850008");
  root.style.setProperty("--accent", c.accent || c.primary || "#f10d1d");

  if (arena) {
    [...arena.classList].filter(x => x.startsWith("theme-")).forEach(x => arena.classList.remove(x));
    arena.classList.add(`theme-${theme.id}`);
    arena.classList.remove("background-image-mode","background-css-mode");
    const bg = theme.background || {};
    if (bg.mode === "image" && bg.image) {
      root.style.setProperty("--bg-image", `url("${bg.image}")`);
      root.style.setProperty("--bg-overlay", String(bg.overlay ?? .58));
      arena.classList.add("background-image-mode");
    } else arena.classList.add("background-css-mode");
  }

  if (theme.club?.logo) {
    document.querySelectorAll(".logo-frame img, .neutral-logo-frame img, .summary-logo-frame img")
      .forEach(img => { if (img.getAttribute("src") !== theme.club.logo) img.src = theme.club.logo; });
  }
  const web = document.getElementById("clubWebsite");
  if (web && theme.club?.website) web.textContent = theme.club.website;
}

// =========================================================
// V2.9 – Display Mode Switcher
// =========================================================
function setScoreboardMode(mode) {
  scoreboardMode = mode === "total" ? "total" : "full";
  localStorage.setItem("scoreboardV2Mode", scoreboardMode);
  const arena = document.querySelector(".arena");
  if (arena) {
    arena.classList.toggle("mode-total", scoreboardMode === "total");
    arena.classList.toggle("mode-full", scoreboardMode === "full");
  }
  document.querySelectorAll(".mode-switcher button").forEach(b =>
    b.classList.toggle("active", b.dataset.mode === scoreboardMode)
  );
  if (latestRenderState) applyScene(latestRenderState);
}

// Persisted V2 display preferences; an unchanged config poll must not reset the timer.
let displayPreferences = {mode: "rotate", intervalSeconds: 30};
let nextAutoModeSwitch = Date.now() + 30000;
function setDisplayPreferences(preferences) {
  const next = preferences || {mode: "rotate", intervalSeconds: 30};
  const changed = next.mode !== displayPreferences.mode || next.intervalSeconds !== displayPreferences.intervalSeconds;
  displayPreferences = {...next};
  const controls = document.querySelector(".mode-switcher");
  if (controls) controls.hidden = next.mode !== "rotate";
  if (next.mode === "compact") setScoreboardMode("total");
  else if (next.mode === "detail") setScoreboardMode("full");
  if (changed) nextAutoModeSwitch = Date.now() + next.intervalSeconds * 1000;
}
function autoRotateScoreboardMode() {
  if (displayPreferences.mode !== "rotate") return;
  if (!latestRenderState?.active?.length) {
    nextAutoModeSwitch = Date.now() + displayPreferences.intervalSeconds * 1000;
    return;
  }
  if (Date.now() >= nextAutoModeSwitch) {
    setScoreboardMode(scoreboardMode === "total" ? "full" : "total");
    nextAutoModeSwitch = Date.now() + displayPreferences.intervalSeconds * 1000;
  }
}
setInterval(autoRotateScoreboardMode, 1000);
// Apply initial view classes without rendering manual view controls.
setScoreboardMode(scoreboardMode);


// Web4Sport -> vorhandenes Scoreboard-Datenmodell.
// Web4Sport liefert Satzdaten, aber keine verifizierten Live-Ballpunkte.
function convertWeb4Sport(raw) {
  if (!Array.isArray(raw.matches) || !raw.matches.length) {
    throw new Error("Web4Sport: keine Begegnungen");
  }
  const teamScore = raw.team_score || {home:0, away:0};
  const game = {source:"web4sport", id:String(raw.sid || "1024564")};
  const teams = {
    home:raw.teams?.home?.trim() || "HEIM",
    away:raw.teams?.away?.trim() || "GAST"
  };
  const unfinished = raw.matches.filter(m => !m.finished);
  // Ohne Tischzuordnung zeigen wir die nächsten drei offenen Paarungen,
  // nicht vermeintlich tatsächlich laufende Tische.
  const selected = unfinished.slice(0,3);
  const boards = selected.map((m, i) => ({
    active:true, hasGame:true, slot:i+1, game, teams, teamScore,
    match:{
      id:`web4sport-${game.id}-${m.number}`,
      state:"InProgress",
      type:String(m.home_position || "").startsWith("D") ? "Double" : "Single"
    },
    sideOne:{
      players:String(m.home || "").split(/\s*\/\s*/).filter(Boolean),
      sets:Number(m.sets_won?.home || 0), points:0, serving:false
    },
    sideTwo:{
      players:String(m.away || "").split(/\s*\/\s*/).filter(Boolean),
      sets:Number(m.sets_won?.away || 0), points:0, serving:false
    }
  }));
  // Auch bei vollständig abgeschlossener Partie Gesamtstand zeigen.
  if (!boards.length) boards.push({
    active:false, hasGame:true, slot:1, game, teams, teamScore,
    match:{id:`web4sport-${game.id}-summary`,state:"Finished",type:"Single"}
  });
  return {scoreboards:boards};
}

async function setDataSource(source, persist = true) {
  if (persist && window.v2SaveSource) {
    try { await window.v2SaveSource(source); } catch (error) { document.getElementById("statusBadge").textContent = error.message; return; }
  }
  dataSource = source === "web4sport" ? "web4sport" : "janova";
  localStorage.setItem("ttsvV2DataSource", dataSource);
  document.body.classList.toggle("source-web4sport", dataSource === "web4sport");
  previousTeamScore = null;
  previousGameKey = null;
  previousValues.clear();
  latestRenderState = null;
  highlightUntil = 0;
  if (highlightTimer) clearTimeout(highlightTimer);
  document.getElementById("pointCall")?.classList.remove("show");
  document.getElementById("games")?.replaceChildren();
  switchScene("neutral");
  refresh();
}

