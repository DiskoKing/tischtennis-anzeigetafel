/* Shared UI for scoreboard 2.0 and its local configuration page. */
(() => {
  let token;
  let observedVersion;
  let offeredUpdate;
  let updateResultTime;
  let current;
  let formLoaded = false;
  let displaySignature;
  let sponsorSignature;
  let sponsorTimer;
  let sponsorListSignature;
  let pendingSponsorFiles = [];
  let pendingBackgroundPreview = '';
  const settings = document.body.classList.contains('settings-page');
  const $ = id => document.getElementById(id);

  async function api(path, options = {}) {
    if (options.method && !token) token = (await api('/api/session')).csrf;
    const response = await fetch(path, {
      cache: 'no-store', ...options,
      headers: {...(options.body instanceof Blob ? {} : {'Content-Type': 'application/json'}),
        ...(options.method ? {'X-Scoreboard-CSRF': token} : {}), ...options.headers}
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Anfrage fehlgeschlagen');
    return result;
  }

  async function saveSource(source) {
    current = await api('/api/config', {method: 'POST', body: JSON.stringify({dataSource: source})});
  }
  window.v2SaveSource = saveSource;

  function apply(config) {
    if (observedVersion && config.version !== observedVersion) { location.reload(); return; }
    observedVersion = config.version;
    document.querySelectorAll('[data-app-version]').forEach(el => { el.textContent = config.version; });
    document.title = 'Anzeigetafel ' + config.version + (settings ? ' · Einstellungen' : '');
    current = config;
    if (settings) return;
    document.querySelector('.arena').style.setProperty('--footer-h', (config.display.footerHeightPercent ?? 8.5) + 'vh');
    document.querySelector('.arena').classList.toggle('compact-stacked', config.display.compactLayout === 'stacked');
    document.querySelector('.arena').classList.toggle('source-manual', config.dataSource === 'manual');
    applySponsors(config.sponsors);
    const signature = JSON.stringify([config.display, config.dataSource]);
    if (signature !== displaySignature) {
      setDisplayPreferences(config.dataSource === 'manual' ? {...config.display, mode: 'compact'} : config.display);
      displaySignature = signature;
    }
    const p = config.club.primary;
    const dark = '#' + p.slice(1).match(/../g).map(v => Math.round(parseInt(v, 16) * .5).toString(16).padStart(2, '0')).join('');
    applyTheme({id: 'custom', colors: {primary: p, primaryDark: dark, border: p, accent: p},
      club: {logo: config.club.logo, website: config.club.website || ' '},
      background: {mode: config.background.image ? 'image' : 'css',
        image: config.background.image, overlay: config.background.overlayPercent / 100}, cardOpacity: .8});
    document.documentElement.style.setProperty('--v2-background', config.club.background);
    document.querySelectorAll('.logo-frame img, .neutral-logo-frame img, .summary-logo-frame img')
      .forEach(img => img.alt = config.club.name || 'Vereinslogo');
    if (typeof dataSource !== 'undefined' && dataSource !== config.dataSource) setDataSource(config.dataSource, false);
  }

  function applySponsors(sponsors) {
    const strip = document.querySelector('.sponsor-strip');
    if (!strip) return;
    const signature = JSON.stringify([sponsors?.enabled, sponsors?.intervalSeconds, sponsors?.items]);
    const existingIntro = $('sponsors-intro');
    if (existingIntro) {
      existingIntro.textContent = sponsors?.introText ?? 'unterstützt von:';
      existingIntro.hidden = !existingIntro.textContent;
    }
    if (signature === sponsorSignature) return;
    sponsorSignature = signature;
    if (sponsorTimer) { clearInterval(sponsorTimer); sponsorTimer = null; }
    let box = $('sponsors-display');
    if (!box) {
      box = document.createElement('div'); box.id = 'sponsors-display';
      box.className = 'sponsors-display'; box.setAttribute('aria-label', 'Sponsoren');
      strip.appendChild(box);
    }
    box.replaceChildren();
    const items = sponsors?.items || [];
    box.hidden = !sponsors?.enabled || !items.length;
    if (box.hidden) return;
    const intro = document.createElement('span'); intro.id = 'sponsors-intro';
    intro.className = 'sponsors-intro'; intro.textContent = sponsors.introText ?? 'unterstützt von:';
    intro.hidden = !intro.textContent; box.appendChild(intro);
    const image = document.createElement('img');
    box.appendChild(image);
    let index = 0;
    const show = () => { image.src = items[index].logo; image.alt = items[index].name; };
    show();
    if (items.length > 1) sponsorTimer = setInterval(() => {
      index = (index + 1) % items.length; show();
    }, sponsors.intervalSeconds * 1000);
  }

  function renderSponsorList(sponsors) {
    const signature = JSON.stringify(sponsors.items);
    if (sponsorListSignature === signature) return;
    sponsorListSignature = signature;
    const list = $('sponsor-logos'); list.replaceChildren();
    $('sponsors-empty').hidden = !!sponsors.items.length;
    for (const item of sponsors.items) {
      const row = document.createElement('div'); row.className = 'sponsor-logo-row';
      const image = document.createElement('img'); image.src = item.logo; image.alt = item.name;
      const label = document.createElement('span'); label.textContent = item.name;
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'secondary'; remove.textContent = 'Entfernen';
      remove.addEventListener('click', async () => {
        remove.disabled = true;
        try {
          const config = await api('/api/sponsors/remove', {method: 'POST', body: JSON.stringify({id: item.id})});
          renderSponsorList(config.sponsors);
          $('sponsor-status').textContent = 'Logo entfernt.';
        } catch (error) { $('sponsor-status').textContent = error.message; remove.disabled = false; }
      });
      row.append(image, label, remove); list.appendChild(row);
    }
  }

  async function uploadPendingSponsors() {
    let index = 0;
    const total = pendingSponsorFiles.length;
    while (pendingSponsorFiles.length) {
      const file = pendingSponsorFiles[0];
      if (file.size > 10 * 1024 * 1024) throw new Error('Ein Logo darf höchstens 10 MB groß sein.');
      $('sponsor-status').textContent = `Logo ${++index} von ${total} wird gespeichert …`;
      const config = await api('/api/sponsors/upload', {method: 'POST',
        headers: {'Content-Type': file.type, 'X-Logo-Name': encodeURIComponent(file.name)}, body: file});
      pendingSponsorFiles.shift();
      renderSponsorList(config.sponsors);
    }
    if (total) {
      $('sponsors-files').value = '';
      $('sponsor-status').textContent = 'Sponsorenlogos gespeichert.';
    }
  }

  function gameButtons(box, games, selected) {
    box.replaceChildren();
    for (const game of games || []) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'game-choice';
      const title = document.createElement('strong');
      title.textContent = game.label;
      const detail = document.createElement('span');
      detail.textContent = `${game.date || 'Datum unbekannt'} · SID ${game.sid}` +
        (selected && selected.sid === game.sid && selected.said === game.said ? ' · ausgewählt' : '');
      button.append(title, detail);
      button.addEventListener('click', async () => {
        button.disabled = true;
        try {
          await api('/api/game', {method: 'POST', body: JSON.stringify({said: game.said, sid: game.sid})});
          if ($('save-status')) $('save-status').textContent = 'Spiel ausgewählt. Daten werden geladen.';
          if ($('v2-message')) $('v2-message').textContent = 'Spiel ausgewählt. Daten werden geladen.';
          await poll();
        } catch (error) {
          if ($('save-status')) $('save-status').textContent = error.message;
          if ($('v2-message')) $('v2-message').textContent = error.message;
        } finally { button.disabled = false; }
      });
      box.appendChild(button);
    }
  }

  window.v2DataState = raw => {
    document.getElementById('neutralScene').classList.toggle('v2-waiting', raw.status !== 'ready');
    if (raw.status === 'ready') return false;
    if (typeof switchScene === 'function') switchScene('neutral');
    const badge = $('statusBadge');
    badge.textContent = raw.message || 'Warte auf Daten';
    if (raw.status === 'selection_required') {
      badge.textContent += ' Bitte Spiel in den Einstellungen auswählen.';
    }
    badge.classList.remove('ok');
    return true;
  };

  function fillForm(config) {
    current = config;
    $('club-name').value = config.club.name;
    $('club-website').value = config.club.website;
    $('primary').value = config.club.primary;
    $('background').value = config.club.background;
    $('background-mode').value = config.background.mode;
    $('background-dim').value = config.background.overlayPercent;
    $('background-file-state').textContent = config.background.customSet ? 'Ein eigenes Hintergrundbild ist gespeichert.' : 'Noch kein eigenes Hintergrundbild gespeichert.';
    $('data-source').value = config.dataSource;
    $('manual-opponent').value = config.manual.opponent;
    updateDataSourceFields();
    $('display-mode').value = config.display.mode;
    $('compact-layout').value = config.display.compactLayout || 'inline';
    $('web-match-count').value = config.display.web4sportMatchCount ?? 2;
    $('display-seconds').value = config.display.intervalSeconds;
    $('footer-height').value = config.display.footerHeightPercent ?? 8.5;
    $('footer-height-label').textContent = 'Höhe der Fußleiste: ' + Number($('footer-height').value).toLocaleString('de-DE') + ' %';
    $('sponsors-enabled').checked = config.sponsors.enabled;
    $('sponsors-seconds').value = config.sponsors.intervalSeconds;
    $('sponsors-intro-text').value = config.sponsors.introText ?? 'unterstützt von:';
    renderSponsorList(config.sponsors);
    updateDisplayFields();
    $('janova-id').value = config.janova.refereeId;
    $('web-username').value = config.web4sport.username;
    $('web-password').placeholder = config.web4sport.passwordSet ? 'Gespeichert – leer lassen zum Beibehalten' : 'Passwort eingeben';
    $('logo-preview').src = config.club.logo;
    $('club-logo-state').textContent = 'Aktuelles Vereinslogo ist gespeichert. Die Datei-Auswahl ist nur für einen Austausch.';
    formLoaded = true;
    preview();
  }

  function preview() {
    updateDisplayFields();
    document.documentElement.style.setProperty('--settings-accent', $('primary').value);
    $('design-preview').style.backgroundColor = $('background').value;
    const mode = $('background-mode').value;
    const dim = Number($('background-dim').value) / 100;
    const image = mode === 'classic' ? 'assets/v1-background.jpg' : mode === 'original' ? 'assets/default-background.svg' : mode === 'custom' ? pendingBackgroundPreview || current?.background?.customImage : '';
    $('background-dim-label').textContent = `Abdunklung: ${$('background-dim').value} %`;
    $('background-dim').disabled = mode === 'css';
    $('design-preview').style.backgroundImage = image ? `linear-gradient(rgba(0,0,0,${dim}),rgba(0,0,0,${dim})),url("${image}")` : 'none';
    $('design-preview').style.backgroundSize = 'cover';
    $('design-preview').style.backgroundPosition = 'center';
    $('preview-name').textContent = $('club-name').value || 'Mein Verein';
    $('preview-website').textContent = $('club-website').value;
    $('preview-score').style.background = $('primary').value;
  }

  function updateDataSourceFields() {
    const source = $('data-source').value;
    $('manual-settings').hidden = source !== 'manual';
    $('manual-opponent').disabled = source !== 'manual';
    $('display-mode').disabled = source === 'manual';
    $('display-mode').closest('label').hidden = source === 'manual';
    $('display-seconds').closest('label').hidden = source === 'manual';
    $('category-games').hidden = source === 'manual';
    $('web-match-options').hidden = source !== 'web4sport';
    $('web-match-options').disabled = source !== 'web4sport';
    for (const [name, id] of [['janova', 'janova-settings'], ['web4sport', 'web4sport-settings']]) {
      const group = $(id);
      group.hidden = name !== source;
      group.disabled = name !== source;
    }
  }

  function updateDisplayFields() {
    if (!$('display-mode')) return;
    $('display-seconds').disabled = $('display-mode').value !== 'rotate';
  }

  async function poll() {
    try {
      const [config, state] = await Promise.all([api('/api/config'), api('/api/state')]);
      apply(config);
      if (settings) {
        if (!formLoaded) fillForm(config);
        if (config.lastUpdate && config.lastUpdate.time !== updateResultTime) {
          updateResultTime = config.lastUpdate.time;
          $('update-status').textContent = config.lastUpdate.message;
        }
        renderSponsorList(config.sponsors);
        $('reader-status').textContent = state.message || 'Warte auf Daten';
        $('reader-status').dataset.status = state.status;
        const signature = JSON.stringify([state.candidates || [], config.web4sport.selection]);
        if ($('games').dataset.signature !== signature) {
          gameButtons($('games'), state.candidates || [], config.web4sport.selection);
          $('games').dataset.signature = signature;
        }
        $('games-empty').hidden = !!state.candidates?.length;
      }
    } catch (error) {
      if (settings) $('reader-status').textContent = error.message;
      else if ($('statusBadge')) $('statusBadge').textContent = 'V2-Server nicht erreichbar';
    }
  }

  async function mount() {
    if (settings) {
      $('footer-height').addEventListener('input', () => {
        $('footer-height-label').textContent = 'Höhe der Fußleiste: ' + Number($('footer-height').value).toLocaleString('de-DE') + ' %';
      });
      const categories = [...document.querySelectorAll('.settings-category')];
      $('expand-sections').addEventListener('click', () => {
        for (const category of categories) category.open = true;
      });
      $('collapse-sections').addEventListener('click', () => {
        for (const category of categories) category.open = false;
      });
      try {
        const saved = JSON.parse(sessionStorage.getItem('anzeigetafel-settings-sections') || '{}');
        for (const category of categories) if (typeof saved[category.id] === 'boolean') category.open = saved[category.id];
      } catch (_) {}
      for (const category of categories) category.addEventListener('toggle', () => {
        try { sessionStorage.setItem('anzeigetafel-settings-sections', JSON.stringify(Object.fromEntries(categories.map(item => [item.id, item.open])))); } catch (_) {}
      });
      document.addEventListener('invalid', event => {
        if (event.target.form !== $('config-form')) return;
        for (let parent = event.target.parentElement; parent; parent = parent.parentElement) {
          if (parent.tagName === 'DETAILS') parent.open = true;
        }
      }, true);
      $('data-source').addEventListener('change', updateDataSourceFields);
      $('update-check').addEventListener('click', async () => {
        $('update-check').disabled = true;
        $('update-install').hidden = true; $('update-download').hidden = true;
        $('update-status').textContent = 'Veröffentlichte Version wird geprüft …';
        try {
          const release = await api('/api/update/check', {method:'POST', body:'{}'});
          offeredUpdate = release.latest;
          $('update-status').textContent = release.available ? 'Version ' + release.latest + ' ist verfügbar.' : 'Version ' + release.installed + ' ist aktuell.';
          $('update-notes').textContent = release.notes; $('update-notes').hidden = !release.notes;
          $('update-install').hidden = !release.available || !release.installSupported;
          $('update-download').href = release.releaseUrl;
          $('update-download').hidden = !release.available || release.installSupported;
          if (release.available && !release.installSupported) $('update-status').textContent += ' Bitte das vollständige Paket herunterladen.';
        } catch (error) { $('update-status').textContent = error.message; }
        finally { $('update-check').disabled = false; }
      });
      $('update-install').addEventListener('click', async () => {
        if (!window.confirm('Update installieren? Die Anzeigetafel wird kurz beendet und neu gestartet. Bitte vorher ungespeicherte Einstellungen speichern.')) return;
        $('update-install').disabled = true; $('update-check').disabled = true;
        $('update-status').textContent = 'Update wird heruntergeladen und geprüft. Bitte nicht beenden …';
        try {
          const result = await api('/api/update/install', {method:'POST', body:JSON.stringify({version:offeredUpdate})});
          $('update-status').textContent = result.message;
        } catch (error) {
          $('update-status').textContent = error.message;
          $('update-install').disabled = false; $('update-check').disabled = false;
          $('update-download').hidden = false;
        }
      });
      const embedded = new URLSearchParams(location.search).get('embedded') === '1';
      if (embedded) {
        document.body.classList.add('is-embedded');
        document.addEventListener('keydown', event => {
          if (event.key === 'Escape') window.parent.postMessage({type: 'v2-close-settings'}, location.origin);
        });
      }
      $('janova-login').addEventListener('click', async () => {
        const button = $('janova-login');
        button.disabled = true;
        $('janova-login-status').textContent = 'Janova-Anmeldung läuft …';
        try {
          const result = await api('/api/janova/login', {method: 'POST', body: JSON.stringify({
            email: $('janova-email').value, password: $('janova-password').value
          })});
          $('janova-id').value = result.refereeId;
          $('janova-login-status').textContent = 'ID übernommen. Bitte Einstellungen speichern.';
        } catch (error) { $('janova-login-status').textContent = error.message; }
        finally { $('janova-password').value = ''; button.disabled = false; }
      });
      $('sponsors-files').addEventListener('change', () => {
        pendingSponsorFiles = [...$('sponsors-files').files];
        $('sponsor-status').textContent = pendingSponsorFiles.length ?
          `${pendingSponsorFiles.length} Logo(s) ausgewählt – mit „Einstellungen speichern“ übernehmen.` : '';
      });
      $('config-form').addEventListener('input', preview);
      $('background-file').addEventListener('change', () => {
        const file = $('background-file').files[0];
        if (file) {
          if (pendingBackgroundPreview) URL.revokeObjectURL(pendingBackgroundPreview);
          pendingBackgroundPreview = URL.createObjectURL(file);
          $('background-mode').value = 'custom';
          $('background-file-state').textContent = 'Neues Hintergrundbild ausgewählt – noch nicht gespeichert.';
          preview();
        }
      });
      $('club-logo').addEventListener('change', () => {
        const file = $('club-logo').files[0];
        if (file) {
          $('logo-preview').src = URL.createObjectURL(file);
          $('club-logo-state').textContent = 'Neues Logo ausgewählt – noch nicht gespeichert.';
        }
      });
      $('config-form').addEventListener('submit', async event => {
        event.preventDefault();
        const button = $('save'); button.disabled = true;
        $('save-status').textContent = 'Wird gespeichert …';
        try {
          if ($('background-mode').value === 'custom' && !$('background-file').files[0] && !current.background.customSet)
            throw new Error('Bitte ein eigenes Hintergrundbild auswählen oder eine andere Darstellung wählen.');
          await uploadPendingSponsors();
          const backgroundFile = $('background-file').files[0];
          if (backgroundFile) {
            if (backgroundFile.size > 10 * 1024 * 1024) throw new Error('Hintergrundbild darf höchstens 10 MB groß sein.');
            await api('/api/background', {method: 'POST', headers: {'Content-Type': backgroundFile.type}, body: backgroundFile});
          }
          let file = $('club-logo').files[0];
          if (file) {
            if (file.size > 10 * 1024 * 1024) throw new Error('Logo darf höchstens 10 MB groß sein.');
            await api('/api/logo', {method: 'POST', headers: {'Content-Type': file.type}, body: file});
          }
          const config = await api('/api/config', {method: 'POST', body: JSON.stringify({
            dataSource: $('data-source').value,
            manual: {opponent: $('data-source').value === 'manual' ? $('manual-opponent').value : current.manual.opponent},
            background: {mode: $('background-mode').value, overlayPercent: Number($('background-dim').value)},
            display: {compactLayout: $('compact-layout').value, mode: $('display-mode').value, intervalSeconds: Number($('display-seconds').value), footerHeightPercent: Number($('footer-height').value), web4sportMatchCount: Number($('web-match-count').value)},
            sponsors: {enabled: $('sponsors-enabled').checked, intervalSeconds: Number($('sponsors-seconds').value), introText: $('sponsors-intro-text').value},
            club: {name: $('club-name').value, website: $('club-website').value,
              primary: $('primary').value, background: $('background').value},
            janova: {refereeId: $('janova-id').value},
            web4sport: {username: $('web-username').value, password: $('web-password').value,
              clearPassword: $('clear-password').checked}
          })});
          $('web-password').value = ''; $('club-logo').value = ''; $('clear-password').checked = false;
          $('background-file').value = '';
          if (pendingBackgroundPreview) URL.revokeObjectURL(pendingBackgroundPreview);
          pendingBackgroundPreview = '';
          fillForm(config);
          $('save-status').textContent = 'Gespeichert. Geöffnete V2-Anzeigen übernehmen das Design automatisch.';
          if (embedded) window.parent.postMessage({type: 'v2-config-saved'}, location.origin);
          await poll();
        } catch (error) { $('save-status').textContent = error.message; }
        finally { button.disabled = false; }
      });
      $('automatic').addEventListener('click', async () => {
        try {
          await api('/api/game', {method: 'POST', body: JSON.stringify({automatic: true})});
          $('save-status').textContent = 'Automatische Auswahl aktiv. Bei mehreren Spielen erscheint die Auswahl.';
          await poll();
        } catch (error) { $('save-status').textContent = error.message; }
      });
      $('reconnect').addEventListener('click', async () => {
        try {
          await api('/api/reconnect', {method: 'POST', body: '{}'});
          $('save-status').textContent = 'Reader verbindet neu.';
        } catch (error) { $('save-status').textContent = error.message; }
      });
    } else {
      const controls = document.createElement('nav');
      controls.className = 'v2-settings-link';
      const button = document.createElement('button'); button.type = 'button'; button.textContent = '⚙'; button.setAttribute('aria-label', 'Einstellungen öffnen'); button.title = 'Einstellungen öffnen';
      const dialog = document.createElement('dialog'); dialog.className = 'v2-settings-dialog';
      dialog.setAttribute('aria-label', 'Einstellungen der Anzeigetafel');
      const bar = document.createElement('div'); bar.className = 'v2-dialog-bar';
      const title = document.createElement('strong'); title.append('Einstellungen · Anzeigetafel '); const dialogVersion = document.createElement('span'); dialogVersion.dataset.appVersion = ''; dialogVersion.textContent = '…'; title.append(dialogVersion);
      const close = document.createElement('button'); close.type = 'button'; close.textContent = 'Zur Anzeigetafel ✕';
      close.addEventListener('click', () => dialog.close());
      const frame = document.createElement('iframe'); frame.title = 'Konfiguration';
      bar.append(title, close); dialog.append(bar, frame); document.body.appendChild(dialog);
      window.v2OpenSettings = () => {
        frame.src = 'settings.html?embedded=1'; dialog.showModal();
      };
      button.addEventListener('click', window.v2OpenSettings);
      dialog.addEventListener('close', async () => {
        frame.src = 'about:blank';
        await poll();
        if (typeof refresh === 'function') refresh();
      });
      window.addEventListener('message', event => {
        if (event.origin !== location.origin || event.source !== frame.contentWindow) return;
        if (event.data?.type === 'v2-close-settings') dialog.close();
        if (event.data?.type === 'v2-config-saved') poll();
      });
      controls.appendChild(button); document.body.appendChild(controls);
    }
    await poll();
    setInterval(poll, 5000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
