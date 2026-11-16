/* Local manual controls. No network listener or global keyboard hook required. */
(() => {
  const boxes = [...document.querySelectorAll('[data-manual-controls]')];
  const keyboard = !document.body.classList.contains('settings-page') || document.body.classList.contains('manual-remote');
  let state, token, busy = false, pollError = false;
  const messages = [];
  const totalTimers = new Map();
  const totalTargets = [['summaryHomeTotal','home'],['summaryAwayTotal','away']];
  async function request(path, body, retried=false) {
    if (body && !token) token = (await request('/api/session')).csrf;
    const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),8000);
    let response;
    try { response = await fetch(path, {signal:controller.signal,cache:'no-store', ...(body ? {method:'POST',headers:{'Content-Type':'application/json','X-Scoreboard-CSRF':token},body:JSON.stringify(body)} : {})}); }
    catch(error){if(body&&!retried)return request(path,body,true);throw new Error('Verbindung unterbrochen. Bitte aktuellen Spielstand prüfen.');}
    finally{clearTimeout(timeout);}
    const data = await response.json();
    if (response.status===403 && body && !retried) { token=null;return request(path,body,true); }
    if (!response.ok) throw new Error(data.error || 'Aktion fehlgeschlagen');
    return data;
  }
  function paint() {
    for (const [id,side] of totalTargets) {
      const el=document.getElementById(id);
      if (!el) continue;
      el.classList.toggle('manual-total-target',!!state?.enabled);
      if (state?.enabled) {
        el.setAttribute('role','button');el.tabIndex=0;
        el.title='Klick: +1 · zwei schnelle Klicks: −1';
        el.setAttribute('aria-label',(side==='home'?'Heim':'Gast')+' zählen. Klick plus eins, zwei schnelle Klicks minus eins.');
      } else {
        el.removeAttribute('role');el.removeAttribute('tabindex');el.removeAttribute('title');el.removeAttribute('aria-label');
      }
    }
    for (const box of boxes) {
      box.querySelectorAll('button').forEach(b => b.disabled = busy || !state?.enabled);
      for (const side of ['home','away']) {
        box.querySelector('[data-name="'+side+'"]').textContent = state?.[side+'Name'] || (side==='home'?'Heim':'Gast');
        box.querySelector('[data-value="'+side+'"]').textContent = state?.[side] ?? 0;
      }
    }
  }
  for (const [id,side] of totalTargets) {
    const el=document.getElementById(id);
    if (!el) continue;
    el.addEventListener('click',event=>{
      if (!state?.enabled || document.querySelector('dialog[open]')) return;
      event.preventDefault();
      const pending=totalTimers.get(side);
      if (pending) {
        clearTimeout(pending.timer);totalTimers.delete(side);
        if (pending.gameId===state.gameId) change(side,-1);
      } else {
        const gameId=state.gameId;
        const timer=setTimeout(()=>{
          totalTimers.delete(side);
          if (state?.enabled && state.gameId===gameId) change(side,1);
        },400);
        totalTimers.set(side,{timer,gameId});
      }
    });
    el.addEventListener('dblclick',event=>event.preventDefault());
    el.addEventListener('keydown',event=>{
      if (!state?.enabled || !['Enter',' '].includes(event.key))return;
      event.preventDefault();if(!event.repeat)change(side,event.shiftKey?-1:1);
    });
  }
  async function change(side, delta, reset=false) {
    if (busy || !state?.enabled) return;
    busy=true;paint();
    try {
      // randomUUID requires HTTPS/localhost; getRandomValues also works on LAN HTTP.
      const eventId = [...crypto.getRandomValues(new Uint8Array(16))].map(n=>n.toString(16).padStart(2,'0')).join('');
      state = await request('/api/manual', {gameId:state.gameId,eventId,...(reset?{action:'reset'}:{side,delta})});
      messages.forEach(m=>m.textContent='Gespeichert.');
      if (typeof window.refresh === 'function') window.refresh();
    } catch (e) { messages.forEach(m=>m.textContent=e.message); }
    finally { busy=false;paint(); }
  }
  for (const box of boxes) {
    const grid=document.createElement('div');grid.className='manual-grid';
    for (const side of ['home','away']) {
      const card=document.createElement('div');card.className='manual-side';
      const label=document.createElement('strong');label.dataset.name=side;
      const score=document.createElement('output');score.className='manual-value';score.dataset.value=side;
      const buttons=document.createElement('div');buttons.className='manual-buttons';
      for (const delta of [1,-1]) {
        const b=document.createElement('button');b.type='button';b.textContent=delta===1?'+':'−';
        b.setAttribute('aria-label',(side==='home'?'Heim':'Gast')+(delta===1?' plus eins':' minus eins'));
        b.addEventListener('click',()=>change(side,delta));buttons.append(b);
      }
      card.append(label,score,buttons);grid.append(card);
    }
    const reset=document.createElement('button');reset.type='button';reset.className='secondary';reset.textContent='Neues Spiel / Zurücksetzen';
    const confirm=document.createElement('div');confirm.hidden=true;confirm.className='manual-reset-confirm';
    const question=document.createElement('p');question.textContent='Beide Spielstände wirklich auf 0 setzen?';
    const yes=document.createElement('button');yes.type='button';yes.textContent='Ja, Spielstand zurücksetzen';
    const no=document.createElement('button');no.type='button';no.textContent='Abbrechen';no.className='secondary';
    let resetGameId;
    reset.addEventListener('click',()=>{resetGameId=state?.gameId;confirm.hidden=false;yes.focus();});
    yes.addEventListener('click',()=>{confirm.hidden=true;if(state?.gameId===resetGameId)change(null,null,true);else messages.forEach(m=>m.textContent='Spiel wurde bereits gewechselt. Bitte erneut prüfen.');});
    no.addEventListener('click',()=>{confirm.hidden=true;reset.focus();});confirm.append(question,yes,no);
    const message=document.createElement('p');message.className='help';message.setAttribute('role','status');messages.push(message);
    box.append(grid,reset,confirm,message);
  }
  async function poll() {
    if (busy) return;
    try {
      const next=await request('/api/manual');
      if (busy) return;
      if(next.enabled&&(pollError||!state?.enabled))messages.forEach(m=>m.textContent='');
      pollError=false;
      state=next;paint();
      if (!state.enabled) messages.forEach(m=>m.textContent='Zuerst Manuelle Eingabe als Datenquelle wählen und Einstellungen speichern.');
    } catch (e) { pollError=true;messages.forEach(m=>m.textContent=e.message); }
  }
  const held = new Set();
  const keys={Numpad7:['home',1],Numpad1:['home',-1],Numpad9:['away',1],Numpad3:['away',-1],F13:['home',1],F14:['home',-1],F15:['away',1],F16:['away',-1]};
  if (keyboard) {
    window.addEventListener('keydown',e=>{
      if (!state?.enabled || !keys[e.code] || e.target.closest?.('input,textarea,select,[contenteditable="true"]') || document.querySelector('dialog[open]')) return;
      e.preventDefault();if(e.repeat || held.has(e.code))return;held.add(e.code);change(...keys[e.code]);
    });
    window.addEventListener('keyup',e=>held.delete(e.code));window.addEventListener('blur',()=>held.clear());
  }
  poll();setInterval(poll,1000);
  window.addEventListener('tt-state-change',poll);
})();
