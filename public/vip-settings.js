/* Independent VIP form; the ordinary configuration form remains unchanged. */
(() => {
  const side=document.querySelector('.settings-side');if(!side)return;
  const groups={
    'Flächen & Rahmen':{background:'Hintergrund',stripe:'Hintergrundstreifen',panel:'Kartenflächen',panelAlt:'Satzkacheln / Nebenflächen',border:'Rahmen',divider:'Trennlinien'},
    'Schrift & Akzente':{heading:'Überschriften',text:'Haupttext',muted:'Neben- und Statustext',accent:'Akzentflächen',accentText:'Text auf Akzentflächen',live:'LIVE-Status',error:'Fehlerhinweise'},
    'Heim, Gast & Ergebnisse':{home:'Heim-Zahlenfeld',homeText:'Heim-Zahl',away:'Gast-Zahlenfeld',awayText:'Gast-Zahl',win:'Siegkachel',winText:'Text auf Siegkachel',loss:'Niederlagenkachel',lossText:'Text auf Niederlagenkachel'}
  };
  const category=document.createElement('details');category.id='category-vip';category.className='settings-card settings-category';
  category.innerHTML=`<summary class="card-heading"><span>VIP</span><h2>VIP-Ansicht</h2></summary><div class="category-content">
    <p>Eigene Ansicht für den VIP-Raum mit zwei Kamerabildern. Vereinslogo und Datenquelle werden aus der normalen Konfiguration übernommen.</p>
    <p><a class="button secondary" href="vip.html" target="_blank" rel="noopener">VIP-Ansicht öffnen ↗</a></p>
    <form id="vip-form"><fieldset><legend>Farben – unabhängig von der Hallenanzeige</legend><div id="vip-color-groups"></div><button id="vip-club-colors" type="button" class="secondary">Vereinsfarben übernehmen</button><p class="help">Übernimmt Akzent, Heim-/Siegfarbe und Hintergrund. Erst mit „VIP-Einstellungen speichern“ anwenden.</p></fieldset>
    <fieldset><legend>Titel & Tischzuordnung</legend><p class="help">Der Titel kommt automatisch aus dem Heimteam: ohne Nummer „1. Mannschaft“, mit II/2 „2. Mannschaft“ usw.</p>
    <label>Zuordnung der Partien<select id="vip-table-rule"><option value="alternating">Abwechselnd auf zwei Tische</option><option value="source">Tischangaben der Quelle verwenden</option><option value="none">Keine Tischzuordnung anzeigen</option></select></label>
    <label>Erste Partie an<select id="vip-first-table"><option value="1">Tisch 1</option><option value="2">Tisch 2</option></select></label><p class="help">click-TT und Web4Sport liefern keine verlässlichen Tischangaben. „Abwechselnd“ ist eure Zuordnungsregel.</p></fieldset>
    <div id="vip-camera-fields"></div>
    <fieldset><legend>Eigene VIP-Fußleiste</legend>
      <label class="check"><input type="checkbox" id="vip-footer-website">Vereinswebsite anzeigen</label>
      <label>Website-Text (optional)<input id="vip-footer-websiteText" maxlength="160" placeholder="Leer = normale Vereinswebsite"></label>
      <label class="check"><input type="checkbox" id="vip-footer-sponsors">Sponsoren anzeigen</label><p class="help">Verwendet die vorhandenen Sponsorenlogos; Ein/Aus und Rotation gelten hier nur für die VIP-Ansicht.</p>
      <label>Einleitender Text<input id="vip-footer-introText" maxlength="160"></label>
      <label>Logo wechseln nach (Sekunden)<input id="vip-footer-intervalSeconds" type="number" min="1" max="3600" step="1"></label>
      <label class="check"><input type="checkbox" id="vip-footer-clock">Uhrzeit und Datum anzeigen</label>
      <label id="vip-height-label" for="vip-footer-heightPercent">Höhe der VIP-Fußleiste</label><input id="vip-footer-heightPercent" type="range" min="4" max="15" step=".5">
    </fieldset>
    <div class="side-actions"><button type="submit">VIP-Einstellungen speichern</button><button id="vip-reconnect" type="button" class="secondary">Kameras neu verbinden</button></div>
    <p id="vip-save-state" role="status" class="help"></p><p id="vip-gateway-state" role="status" class="help"></p>
    <p class="help">RTSP benötigt den optionalen lokalen Kameravermittler. Unter Linux/NUC hält dieser aktivierte Streams für eine schnelle Verbindung offen. Originalweitergabe kann je nach Kamera-Codec im Browser nicht funktionieren.</p></form></div>`;
  side.insertBefore(category,document.getElementById('category-updates'));
  const openFromHash=()=>{if(location.hash==='#category-vip'){category.open=true;category.scrollIntoView({block:'start'});}};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',openFromHash);else openFromHash();
  window.addEventListener('hashchange',openFromHash);
  const $=id=>document.getElementById(id),colors=Object.values(groups).flatMap(Object.keys);
  for(const [title,entries] of Object.entries(groups)){
    const section=document.createElement('details');section.className='vip-palette-group';const summary=document.createElement('summary');summary.textContent=title;section.append(summary);
    const grid=document.createElement('div');grid.className='vip-palette-grid';
    for(const [key,label] of Object.entries(entries)){const wrapper=document.createElement('label');wrapper.textContent=label;const input=document.createElement('input');input.type='color';input.id='vip-color-'+key;wrapper.append(input);grid.append(wrapper);}
    section.append(grid);$('vip-color-groups').append(section);
  }
  for(let i=0;i<2;i++){
    const n=i+1,fieldset=document.createElement('fieldset');fieldset.innerHTML=`<legend>Kamera ${n}</legend>
      <label class="check"><input id="vip-camera-${i}-enabled" type="checkbox">Kamera ${n} aktiv</label>
      <label>Beschriftung · Kamera ${n}<input id="vip-camera-${i}-label" maxlength="80"></label>
      <label>RTSP-Adresse · Kamera ${n}<input id="vip-camera-${i}-url" type="url" maxlength="2048" placeholder="rtsp://192.168.1.10/stream" spellcheck="false" autocomplete="off"></label>
      <label>Benutzername · Kamera ${n}<input id="vip-camera-${i}-username" maxlength="512" autocomplete="off"></label>
      <label>Passwort · Kamera ${n}<input id="vip-camera-${i}-password" type="password" maxlength="512" autocomplete="off"></label>
      <label class="check"><input id="vip-camera-${i}-clearPassword" type="checkbox">Gespeichertes Kamerapasswort entfernen</label>
      <label class="check"><input id="vip-camera-${i}-transcode" type="checkbox">Browserkompatibles H.264, 720p / 15 Bilder pro Sekunde</label>
      <p class="help">Zugangsdaten separat eintragen. Ein leeres Passwort behält das gespeicherte bei. Ausgeschaltete Kameras bauen keine neue Streamverbindung auf.</p>`;
    $('vip-camera-fields').append(fieldset);
  }
  let csrf;
  async function api(path,body){
    if(body&&!csrf)csrf=(await api('/api/session')).csrf;
    const response=await fetch(path,{cache:'no-store',...(body?{method:'POST',headers:{'Content-Type':'application/json','X-Scoreboard-CSRF':csrf},body:JSON.stringify(body)}:{})});
    const data=await response.json();if(!response.ok)throw Error(data.error||'VIP-Einstellungen nicht erreichbar');return data;
  }
  const footerKeys=['website','websiteText','sponsors','clock','introText','intervalSeconds','heightPercent'];
  function height(){const input=$('vip-footer-heightPercent');$('vip-height-label').textContent=`Höhe der VIP-Fußleiste: ${input.value} %`;}
  function fill(value){
    colors.forEach(k=>$('vip-color-'+k).value=value.colors[k]);$('vip-table-rule').value=value.tableRule;$('vip-first-table').value=value.firstTable;
    for(const k of footerKeys){const el=$('vip-footer-'+k);if(el.type==='checkbox')el.checked=value.footer[k];else el.value=value.footer[k];}
    value.cameras.forEach((camera,i)=>{for(const key of ['enabled','label','url','username','transcode']){const el=$(`vip-camera-${i}-${key}`);if(el.type==='checkbox')el.checked=camera[key];else el.value=camera[key];}
      $(`vip-camera-${i}-password`).value='';$(`vip-camera-${i}-clearPassword`).checked=false;$(`vip-camera-${i}-password`).placeholder=camera.passwordSet?'Gespeichert – leer lassen zum Beibehalten':'Optional';});height();
  }
  $('vip-footer-heightPercent').addEventListener('input',height);
  $('vip-club-colors').addEventListener('click',async()=>{try{const config=await api('/api/config'),p=config.club.primary;
    for(const key of ['accent','border','home','win','live'])$('vip-color-'+key).value=p;$('vip-color-background').value=config.club.background;
    const rgb=[1,3,5].map(i=>parseInt(p.slice(i,i+2),16)),fg=rgb.reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0)>140?'#111610':'#ffffff';
    for(const key of ['accentText','homeText','winText'])$('vip-color-'+key).value=fg;$('vip-save-state').textContent='Vereinsfarben übernommen – noch nicht gespeichert.';
  }catch(e){$('vip-save-state').textContent=e.message;}});
  $('vip-form').addEventListener('submit',async event=>{event.preventDefault();const button=$('vip-form').querySelector('[type=submit]');button.disabled=true;
    try{const value={colors:Object.fromEntries(colors.map(k=>[k,$('vip-color-'+k).value])),tableRule:$('vip-table-rule').value,firstTable:Number($('vip-first-table').value),footer:{},cameras:[]};
      for(const key of footerKeys){const el=$('vip-footer-'+key);value.footer[key]=el.type==='checkbox'?el.checked:el.type==='number'||el.type==='range'?Number(el.value):el.value;}
      for(let i=0;i<2;i++){const camera={};for(const key of ['enabled','label','url','username','password','clearPassword','transcode']){const el=$(`vip-camera-${i}-${key}`);camera[key]=el.type==='checkbox'?el.checked:el.value;}value.cameras.push(camera);}
      const result=await api('/api/vip',value);fill(result.config);$('vip-save-state').textContent='VIP-Einstellungen gespeichert. Die VIP-Ansicht übernimmt sie automatisch.';
    }catch(e){$('vip-save-state').textContent=e.message;}finally{button.disabled=false;}
  });
  $('vip-reconnect').addEventListener('click',async()=>{try{await api('/api/vip/reconnect',{});$('vip-save-state').textContent='Kameravermittler wird neu verbunden.';}catch(e){$('vip-save-state').textContent=e.message;}});
  api('/api/vip').then(result=>{fill(result.config);$('vip-gateway-state').textContent=result.gateway.message;}).catch(e=>$('vip-save-state').textContent=e.message);
  setInterval(()=>{if(category.open)api('/api/vip').then(result=>$('vip-gateway-state').textContent=result.gateway.message).catch(()=>{});},5000);
})();
