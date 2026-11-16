(() => {
  const $ = id => document.getElementById(id);
  let csrf, local = false, authenticated = false;
  const labels = {manual:'Manuelle Eingabe',janova:'Janova',web4sport:'TischtennisLive / Web4Sport',clicktt:'myTischtennis / click-TT'};
  async function api(path, body) {
    const response = await fetch(path,{cache:'no-store',...(body ? {method:'POST',headers:{'Content-Type':'application/json','X-Scoreboard-CSRF':csrf},body:JSON.stringify(body)} : {})});
    const value=await response.json();
    if(!response.ok)throw new Error(value.error || 'Verbindung fehlgeschlagen.');
    return value;
  }
  function showAuth(value) {
    authenticated=value; $('remote-login').hidden=value; $('remote-app').hidden=!value;
    if(!value)$('remote-settings-frame').src='about:blank';
    $('remote-logout').hidden=local;
  }
  async function session() {
    const info=await api('/api/session');csrf=info.csrf;local=info.local;showAuth(info.authenticated);
    $('remote-connection').textContent=info.authenticated?'Verbunden · Änderungen werden gespeichert.':'Bitte mit Admin-PIN anmelden.';
  }
  async function status() {
    if(!authenticated)return;
    try {
      const data=await api('/api/system');
      $('remote-source').textContent='Datenquelle: '+(labels[data.dataSource]||data.dataSource);
      const n=data.network;
      const connection={ethernet:'Ethernet',wifi:'WLAN',offline:'Offline',unknown:'Nicht ermittelbar',unsupported:'Nicht unterstützt'};
      const rows=[['Netzwerk',connection[n.connection]||'Unbekannt'],['IP-Adresse',n.ip||'Nicht verfügbar'],['WLAN',n.ssid||'Nicht verfügbar'],['Signal',n.signalPercent==null?'Nicht verfügbar':n.signalPercent+' %'],['Datenquelle',labels[data.dataSource]],['Quellenstatus',data.sourceMessage||data.sourceStatus],['Letzte erfolgreiche Aktualisierung',data.lastSuccessfulUpdate?new Date(data.lastSuccessfulUpdate).toLocaleString('de-DE'):'Noch keine'],['Version',data.version]];
      $('system-values').replaceChildren();
      for(const [name,value] of rows){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=name;dd.textContent=value;$('system-values').append(dt,dd);}
      $('remote-connection').textContent='Verbunden · Änderungen werden gespeichert.';
    }catch(e){$('remote-connection').textContent=e.message;try{await session();}catch{showAuth(false);}}
  }
  $('pin-form').addEventListener('submit',async e=>{
    e.preventDefault();const button=e.submitter;button.disabled=true;
    try {await api('/api/remote/login',{pin:$('remote-pin').value});$('remote-pin').value='';await session();await status();window.dispatchEvent(new Event('tt-state-change'));}
    catch(error){$('remote-connection').textContent=error.message;}
    finally{button.disabled=false;}
  });
  $('remote-logout').addEventListener('click',async()=>{try{await api('/api/remote/logout',{});await session();}catch(e){$('remote-connection').textContent=e.message;}});
  document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{
    for(const name of ['score','settings','system'])$('remote-'+name).hidden=button.dataset.tab!==name;
    document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
    if(button.dataset.tab==='settings'&&(!$('remote-settings-frame').getAttribute('src')||$('remote-settings-frame').getAttribute('src')==='about:blank'))$('remote-settings-frame').src='/settings.html?embedded=1';
  }));
  $('remote-refresh').addEventListener('click',status);
  window.addEventListener('tt-state-change',status);
  session().then(status).catch(e=>{$('remote-connection').textContent=e.message;});setInterval(status,5000);
})();
