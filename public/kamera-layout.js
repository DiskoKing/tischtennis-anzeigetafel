/* VIP rendering: shared source/logo, independent appearance and camera settings. */
(() => {
  const $=s=>document.querySelector(s);
  let busy=false,config,sponsorSignature,sponsorTimer,lastDataSignature;
  function text(selector,value){$(selector).textContent=value;}
  function node(tag,value){const el=document.createElement(tag);el.textContent=value;return el;}
  function table(slot,source){
    const value=config.vip;
    if(value.tableRule==='alternating')return (slot-1+value.firstTable-1)%2+1;
    return value.tableRule==='source'&&source==='janova'?slot:null;
  }
  function applyVip(){
    const value=config.vip;
    for(const [key,color] of Object.entries(value.colors))document.documentElement.style.setProperty('--vip-'+key,color);
    document.documentElement.style.setProperty('--vip-footer-height',value.footer.heightPercent+'%');
    $('.club-footer').hidden=!value.footer.website;$('.clock').hidden=!value.footer.clock;
    text('#club-website',value.footer.websiteText||config.club.website||'');
    sponsors({...config.sponsors,enabled:value.footer.sponsors,intervalSeconds:value.footer.intervalSeconds,introText:value.footer.introText});
    window.vipCameraConfig=value.cameras.map(c=>({enabled:c.enabled,label:c.label}));
    window.dispatchEvent(new CustomEvent('vip-config',{detail:window.vipCameraConfig}));
  }
  function teamTitle(home){
    const suffix=String(home||'').trim().match(/(?:^|\s)([1-9]\d?|[IVXLCDM]+)\.?$/i)?.[1].toUpperCase();
    let number=1;
    if(suffix&&/^\d+$/.test(suffix))number=Number(suffix);
    else if(suffix&&/^(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$/.test(suffix)){
      const values={I:1,V:5,X:10,L:50,C:100};number=0;
      for(let i=0;i<suffix.length;i++)number+=values[suffix[i]]<(values[suffix[i+1]]||0)?-values[suffix[i]]:values[suffix[i]];
    }
    return `${number}. Mannschaft`;
  }
  function clock(){const now=new Date();text('#clock-time',new Intl.DateTimeFormat('de-DE',{hour:'2-digit',minute:'2-digit'}).format(now));text('#clock-date',new Intl.DateTimeFormat('de-DE').format(now));}
  function sponsors(value){
    const signature=JSON.stringify(value);if(signature===sponsorSignature)return;sponsorSignature=signature;
    clearInterval(sponsorTimer);const items=value?.items||[];$('#camera-sponsors').hidden=!value?.enabled||!items.length;
    if($('#camera-sponsors').hidden)return;
    text('#sponsor-intro',value.introText??'unterstützt von:');
    let index=0;const update=()=>{const logos=$('#sponsor-logos');logos.replaceChildren();for(let i=0;i<Math.min(5,items.length);i++){const item=items[(index+i)%items.length],img=document.createElement('img');img.src=item.logo;img.alt=item.name;logos.append(img);}};update();
    if(items.length>5)sponsorTimer=setInterval(()=>{index=(index+5)%items.length;update();},Math.max(1,value.intervalSeconds)*1000);
  }
  async function read(path){
    const response=await fetch(path,{cache:'no-store'});
    if(response.status===401){$('#login-link').hidden=false;throw Error('Bitte zuerst mit der LAN-PIN anmelden.');}
    if(!response.ok)throw Error('Daten nicht erreichbar');
    $('#login-link').hidden=true;return response.json();
  }
  function fit(){
    for(const el of document.querySelectorAll('h1,.header-club,.team strong,.player>strong')){
      el.style.fontSize='';let size=parseFloat(getComputedStyle(el).fontSize);
      if(!el.clientHeight||!el.clientWidth)continue;
      const boundedHeight=!el.matches('h1');
      while((el.scrollWidth>el.clientWidth+1||(boundedHeight&&el.scrollHeight>el.clientHeight+1))&&size>10){size=Math.max(10,size-1);el.style.fontSize=`${size}px`;}
    }
  }
  function show(data){
    if(data.status!=='ready')throw Error(data.message||'Warte auf Spieldaten');
    const boards=(data.scoreboards||[]).filter(b=>b.hasGame),board=boards[0];
    if(!board)throw Error('Noch keine Begegnung gefunden');
    const game=board.game||{},score=board.teamScore||{};
    text('h1',teamTitle(board.teams.home));text('#competition',game.competition||'TISCHTENNIS');
    text('#season',game.season?` · SAISON ${game.season}`:'');
    const date=new Date(game.startedAt);
    text('.headline p',(game.completed?'Beendet':'Heimspiel')+(Number.isFinite(date.getTime())?' · '+new Intl.DateTimeFormat('de-DE',{dateStyle:'medium',timeStyle:'short'}).format(date):''));
    text('.team.home strong',board.teams.home);text('.team.guest strong',board.teams.away);
    const totals=document.querySelectorAll('.result b');totals[0].textContent=score.home;totals[1].textContent=score.away;
    $('.total').setAttribute('aria-label',`Gesamtstand ${score.home} zu ${score.away}`);
    const history=data.history||[],sequence=$('.results');sequence.replaceChildren();
    $('.sequence').hidden=!history.length;
    let singles=0,doubles=0;
    for(const entry of history){
      const item=document.createElement('div');item.className=entry.finished?(entry.homeSets>entry.awaySets?'won':'lost'):'open';
      const label=entry.type==='Double'?`D${++doubles}`:`E${++singles}`;
      const assigned=table(entry.slot,game.source);
      item.append(node('small',label),node('b',entry.finished?`${entry.homeSets}:${entry.awaySets}`:'LIVE'));
      item.title=`${entry.homePlayers.join(' / ')} – ${entry.awayPlayers.join(' / ')} · ${entry.finished?'Beendet':'Laufend'}`;sequence.append(item);
    }
    sequence.style.setProperty('--count',Math.max(1,history.length));
    const matches=$('.matches');matches.replaceChildren();
    const detail=boards.filter(b=>b.sideOne&&b.sideTwo),active=detail.filter(b=>b.active);
    const selected=active.length?active.slice(0,2):detail.slice(-2);
    for(const b of selected){
      const card=document.createElement('article');card.className='match';
      const header=document.createElement('header'),players=document.createElement('div');players.className='players';
      const assigned=table(b.slot,b.game?.source);card.dataset.table=assigned||'';
      header.append(node('h2',(assigned?`Tisch ${assigned} · `:'')+(b.match.type==='Double'?'Doppel':'Einzel')),node('span',b.match.state==='Finished'?'Beendet':b.match.state==='Scheduled'?'Offen':`${Number(b.sideOne.sets||0)+Number(b.sideTwo.sets||0)+1}. Satz`));
      card.title=`Aufstellungsposition ${b.match.label||b.slot}`;
      for(const side of [b.sideOne,b.sideTwo]){
        const row=document.createElement('div');row.className='player';
        const sets=document.createElement('div');sets.className='sets';sets.append(node('small','SÄTZE'),node('b',side.sets));
        const points=node('b',side.points??0);points.className='points';points.hidden=b.match.state==='Finished'||typeof side.points!=='number';
        const names=document.createElement('strong');for(const name of side.players)names.append(node('span',name));
        if(typeof side.points==='number'&&side.points>Math.min(b.sideOne.points,b.sideTwo.points))points.classList.add('leading');row.append(names,sets,points);players.append(row);
      }
      if(b.match.state==='Finished')card.classList.add('finished');
      if(typeof b.sideOne.points!=='number'&&typeof b.sideTwo.points!=='number')card.classList.add('sets-only');
      const setHistory=document.createElement('div');setHistory.className='set-history';
      setHistory.append(node('span','Satzergebnisse'));
      for(const score of b.match.setScores||[])setHistory.append(node('b',`${score.home}:${score.away}`));
      card.append(header,players,setHistory);matches.append(card);
    }
    if(!selected.length){const note=node('p','Aktuell keine einzelnen Paarungen verfügbar.');note.className='no-matches';matches.append(note);}
    $('.scores').classList.toggle('no-history',!history.length);
    const updated=new Date(data.updated);
    text('#source-state',`${game.completed?'ENDSTAND':'QUELLE VERBUNDEN'} · ${config.dataSource==='clicktt'?'myTischtennis / click-TT':config.dataSource} · ${Number.isFinite(updated.getTime())?new Intl.DateTimeFormat('de-DE',{hour:'2-digit',minute:'2-digit'}).format(updated):''}`);
    requestAnimationFrame(fit);
  }
  async function refresh(){
    if(busy)return;busy=true;
    try{
      config=await read('/api/config');text('#club-name',config.club.name);text('#header-club',config.club.name);
      $('#club-logo').src=config.club.logo;$('#club-logo').alt=config.club.name;
      applyVip();
      const data=await read('/api/vip/state'),signature=JSON.stringify([data,config.club,config.vip]);
      if(signature!==lastDataSignature){show(data);lastDataSignature=signature;}
      $('#source-state').classList.remove('error');
    }catch(e){text('#source-state',e.message);$('#source-state').classList.add('error');}
    finally{busy=false;}
  }
  $('#layout-settings').addEventListener('click',()=>$('#view-dialog').showModal());
  clock();setInterval(clock,1000);refresh();setInterval(refresh,3000);window.addEventListener('resize',fit);
})();
