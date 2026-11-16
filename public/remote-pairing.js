/* Reusable local QR panel. PINs never enter a URL or image. */
(() => {
  function mount(box) {
    let signature, busy=false;
    async function refresh(){
      if(busy)return;busy=true;
      try{
        const response=await fetch('/api/remote/pairing',{cache:'no-store'});
        if(!response.ok)throw new Error('QR-Zugang nur direkt am Gerät oder nach Anmeldung verfügbar.');
        const data=await response.json(), next=JSON.stringify(data);
        if(next===signature)return;signature=next;box.replaceChildren();
        if(!data.urls.length){const p=document.createElement('p');p.textContent=!data.enabled?'Fernbedienung ist nicht freigegeben. Zuerst in den Einstellungen PIN und LAN-Freigabe einrichten.':data.restartRequired?'LAN-Einstellungen gespeichert. Bitte den Anzeigetafel-Dienst neu starten.':'Noch keine erreichbare Netzwerkadresse erkannt. WLAN/LAN prüfen; der QR-Code erscheint automatisch.';box.append(p);return;}
        const lead=document.createElement('p');lead.textContent='Mit der Smartphone-Kamera scannen. Beide Geräte müssen im selben Netz sein. Danach mit deiner Admin-PIN anmelden.';box.append(lead);
        const cards=document.createElement('div');cards.className='remote-qr-cards';
        data.urls.forEach((url,index)=>{
          const card=document.createElement('div');card.className='remote-qr-card';
          const image=document.createElement('img');image.src=data.qrImages[index];image.alt='QR-Code zur Fernbedienung: '+url;image.width=240;image.height=240;
          image.addEventListener('error',()=>{signature=null;});
          const link=document.createElement('a');link.href=url;link.textContent=url;card.append(image,link);cards.append(card);
        });box.append(cards);
        if(data.hostnameUrl){const p=document.createElement('p');p.className='help';p.append('Optionaler Gerätename (netzabhängig): ');const a=document.createElement('a');a.href=data.hostnameUrl;a.textContent=data.hostnameUrl;p.append(a);box.append(p);}
        const note=document.createElement('p');note.className='help';note.textContent='Der QR-Code enthält nur die aktuelle Adresse, keine PIN. Nach einem Netzwechsel neu scannen. Gast-WLANs können Verbindungen zwischen Geräten sperren.';box.append(note);
      }catch(error){box.textContent=error.message;signature=null;}finally{busy=false;}
    }
    refresh();setInterval(()=>{if(!box.closest('dialog')||box.closest('dialog').open)refresh();},5000);
    window.addEventListener('tt-pairing-change',refresh);
    return refresh;
  }
  window.TTRemotePairing={mount};
  document.querySelectorAll('[data-remote-pairing]').forEach(mount);
})();
