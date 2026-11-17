import {VideoRTC} from './vendor/go2rtc/video-rtc.js';

class CameraVideo extends VideoRTC {
  constructor(){super();this.mode='mse';this.media='video';this.RECONNECT_TIMEOUT=8000;this.lastTime=-1;this.lastFrame=0;}
  oninit(){
    super.oninit();this.video.controls=false;this.video.muted=true;this.video.autoplay=true;
    this.video.style.objectFit='contain';
    this.video.addEventListener('timeupdate',()=>{if(this.video.currentTime>this.lastTime&&this.video.readyState>=2)this.lastFrame=Date.now();this.lastTime=this.video.currentTime;});
  }
}
customElements.define('tt-camera',CameraVideo);
const views=[...document.querySelectorAll('.camera')].map((panel,index)=>{
  const empty=panel.querySelector('.empty');
  const stage=document.createElement('div');stage.className='video-stage';empty.replaceWith(stage);
  const state=document.createElement('span');state.className='camera-state';state.textContent='Verbinde …';
  const hint=document.createElement('div');hint.className='video-hint';hint.textContent='Kamera wird verbunden …';
  stage.append(hint);panel.querySelector('header>span').replaceWith(state);
  const view={panel,stage,state,hint,index,player:null};
  const timer=setInterval(()=>{
    const player=view.player;if(!player)return;
    const live=player.wsState===WebSocket.OPEN&&player.lastFrame>0&&Date.now()-player.lastFrame<6000;
    state.textContent=live?'● LIVE':'Verbinde …';state.classList.toggle('live',live);
    hint.hidden=live;hint.textContent=player.lastFrame?'Kameraverbindung unterbrochen · verbinde erneut …':'Kamera wird verbunden …';
  },1000);
  window.addEventListener('pagehide',()=>clearInterval(timer),{once:true});
  return view;
});
function configure(cameras){
  for(const view of views){
    const camera=cameras[view.index]||{enabled:false,label:`Kamera ${view.index+1}`};
    view.panel.querySelector('h2').textContent=camera.label||`Kamera ${view.index+1}`;
    if(!camera.enabled){
      if(view.player){view.player.remove();view.player=null;}
      view.state.textContent='AUS';view.state.classList.remove('live');view.hint.hidden=false;view.hint.textContent='Kamera ausgeschaltet';continue;
    }
    if(view.player)continue;
    view.state.textContent='Verbinde …';view.hint.hidden=false;view.hint.textContent='Kamera wird verbunden …';
    const player=document.createElement('tt-camera');view.player=player;view.stage.prepend(player);
    player.src=`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/api/cameras/${view.index+1}/ws`;
  }
}
window.addEventListener('vip-config',event=>configure(event.detail));
configure(window.vipCameraConfig||[]);
