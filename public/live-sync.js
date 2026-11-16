/* One bounded status request per second, no long-lived threads on small devices. */
(() => {
  let revision, busy=false;
  const kiosk=!!document.getElementById('neutralScene');
  let badge;
  if(kiosk){badge=document.createElement('span');badge.className='network-indicator';badge.setAttribute('role','status');document.querySelector('.arena').append(badge);}
  async function poll(){
    if(busy)return;busy=true;
    try{
      const response=await fetch('/api/system',{cache:'no-store'});
      if(!response.ok)throw new Error();
      const state=await response.json();
      if(badge){const title={wifi:'WLAN',ethernet:'LAN',offline:'Offline',unknown:'Netzwerk unbekannt',unsupported:'Netzwerk unbekannt'};badge.textContent='● '+(title[state.network.connection]||'Netzwerk');badge.title='Netzwerkstatus · Datenquelle: '+state.sourceStatus;badge.classList.toggle('offline',state.network.connection==='offline');}
      if(revision!==undefined&&revision!==state.revision)window.dispatchEvent(new Event('tt-state-change'));
      revision=state.revision;
    }catch{if(badge){badge.textContent='● Server nicht erreichbar';badge.classList.add('offline');}}
    finally{busy=false;}
  }
  poll();setInterval(poll,1000);
})();
