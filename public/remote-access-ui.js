(() => {
  const $=id=>document.getElementById(id);
  let csrf;
  async function api(body){
    if(!csrf)csrf=(await(await fetch('/api/session',{cache:'no-store'})).json()).csrf;
    const response=await fetch('/api/remote/access',{cache:'no-store',...(body?{method:'POST',headers:{'Content-Type':'application/json','X-Scoreboard-CSRF':csrf},body:JSON.stringify(body)}:{})});
    const value=await response.json();if(!response.ok)throw new Error(value.error);return value;
  }
  function paint(value){
    $('remote-enabled').checked=value.enabled;$('remote-bind').value=value.bindAddress;
    $('remote-admin-pin').placeholder=value.pinSet?'PIN gespeichert – leer lassen zum Beibehalten':'6 bis 12 Ziffern';
    $('remote-access-state').textContent=value.restartRequired?'Gespeichert. Anzeigetafel-Dienst neu starten, damit sich die Bind-Adresse ändert.':value.enabled?'LAN-Freigabe aktiv.':'LAN-Freigabe deaktiviert.';
    window.dispatchEvent(new Event('tt-pairing-change'));
  }
  $('remote-access-save').addEventListener('click',async()=>{
    const button=$('remote-access-save');button.disabled=true;
    try{const patch={enabled:$('remote-enabled').checked,bindAddress:$('remote-bind').value};if($('remote-admin-pin').value)patch.pin=$('remote-admin-pin').value;paint(await api(patch));$('remote-admin-pin').value='';}
    catch(e){$('remote-access-state').textContent=e.message;}
    finally{button.disabled=false;}
  });
  api().then(paint).catch(e=>{$('category-remote').hidden=true;});
})();
