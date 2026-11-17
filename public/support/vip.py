"""Independent VIP appearance and camera configuration; secrets remain private."""
import copy
import json
import re
import socket
import subprocess
import sys
from urllib.parse import quote, unquote, urlsplit, urlunsplit

COLORS = {
    'background':'#040906','stripe':'#0a160e','panel':'#101710','panelAlt':'#1d2a20',
    'border':'#d1f719','heading':'#f8faf9','text':'#f8faf9','muted':'#aebbb2',
    'accent':'#d1f719','accentText':'#111610','home':'#d1f719','homeText':'#111610',
    'away':'#070c08','awayText':'#ffffff','win':'#d1f719','winText':'#111610',
    'loss':'#c8493e','lossText':'#ffffff','live':'#d1f719','error':'#ff8c7f','divider':'#3b493f',
}


def defaults(club=None):
    colors=copy.deepcopy(COLORS)
    if club:
        for key in ('accent','border','home','win','live'):
            colors[key]=club.get('primary',COLORS[key])
        colors['background']=club.get('background',COLORS['background'])
        rgb=[int(colors['accent'][i:i+2],16) for i in (1,3,5)]
        foreground='#111610' if sum(v*w for v,w in zip(rgb,(.2126,.7152,.0722)))>140 else '#ffffff'
        for key in ('accentText','homeText','winText'):colors[key]=foreground
    return {'colors':colors,'tableRule':'alternating','firstTable':1,
            'footer':{'website':True,'websiteText':'','sponsors':True,'clock':True,'heightPercent':8,
                      'introText':'unterstützt von:','intervalSeconds':10},
            'cameras':[{'enabled':False,'label':f'Kamera {i} · Tisch {i}','url':'','username':'','password':'','transcode':True} for i in (1,2)]}


def rtsp_url(value):
    if not isinstance(value,str) or len(value)>2048 or any(c.isspace() or c in '\\"\'`|;<>' for c in value):
        raise ValueError('RTSP-Adresse ungültig')
    if not value:return ''
    try:
        u=urlsplit(value)
        if u.scheme not in ('rtsp','rtsps') or not u.hostname or u.fragment or u.username is not None or u.password is not None:
            raise ValueError()
        if u.port is not None and not 1<=u.port<=65535:raise ValueError()
        if any(ord(c)<32 for c in unquote(value)):raise ValueError()
        if not re.fullmatch(r'[A-Za-z0-9.:-]+',u.hostname):raise ValueError()
    except ValueError:
        raise ValueError('Bitte eine RTSP-/RTSPS-Adresse ohne Zugangsdaten verwenden. Benutzername und Passwort separat eintragen.') from None
    return value


def validate(previous,patch):
    if not isinstance(patch,dict) or set(patch)-{'colors','tableRule','firstTable','footer','cameras'}:
        raise ValueError('VIP-Einstellungen ungültig')
    result=copy.deepcopy(previous)
    if 'colors' in patch:
        colors=patch['colors']
        if not isinstance(colors,dict) or set(colors)-set(COLORS):raise ValueError('VIP-Farben ungültig')
        for key,value in colors.items():
            if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ValueError('VIP-Farbe ungültig')
            result['colors'][key]=value.lower()
    if 'tableRule' in patch:
        if patch['tableRule'] not in ('alternating','source','none'):raise ValueError('VIP-Tischzuordnung ungültig')
        result['tableRule']=patch['tableRule']
    if 'firstTable' in patch:
        if type(patch['firstTable']) is not int or patch['firstTable'] not in (1,2):raise ValueError('VIP-Starttisch ungültig')
        result['firstTable']=patch['firstTable']
    if 'footer' in patch:
        footer=patch['footer']
        if not isinstance(footer,dict) or set(footer)-set(result['footer']):raise ValueError('VIP-Fußleiste ungültig')
        for key,value in footer.items():
            if key in ('website','sponsors','clock') and type(value) is not bool:raise ValueError('VIP-Fußleiste ungültig')
            if key=='heightPercent' and (type(value) not in (int,float) or not 4<=value<=15):raise ValueError('VIP-Fußleistenhöhe: 4 bis 15 %')
            if key=='intervalSeconds' and (type(value) is not int or not 1<=value<=3600):raise ValueError('VIP-Rotation: 1 bis 3600 Sekunden')
            if key in ('websiteText','introText') and (not isinstance(value,str) or len(value)>160):raise ValueError('VIP-Fußleistentext zu lang')
        result['footer'].update(footer)
    if 'cameras' in patch:
        cameras=patch['cameras']
        if not isinstance(cameras,list) or len(cameras)!=2:raise ValueError('Genau zwei VIP-Kameras konfigurieren')
        for index,camera in enumerate(cameras):
            if not isinstance(camera,dict) or set(camera)-{'enabled','label','url','username','password','clearPassword','transcode'}:
                raise ValueError('VIP-Kamera ungültig')
            target=result['cameras'][index]
            for key in ('enabled','transcode','clearPassword'):
                if key in camera and type(camera[key]) is not bool:raise ValueError('VIP-Kamera ungültig')
            for key in ('label','username','password'):
                if key in camera and (not isinstance(camera[key],str) or len(camera[key])>(80 if key=='label' else 512) or any(ord(c)<32 for c in camera[key])):
                    raise ValueError('VIP-Kamerabeschriftung oder Zugangsdaten ungültig')
            if 'url' in camera:target['url']=rtsp_url(camera['url'].strip() if isinstance(camera['url'],str) else camera['url'])
            for key in ('enabled','transcode','label','username'):
                if key in camera:target[key]=camera[key]
            if camera.get('clearPassword'):target['password']=''
            elif camera.get('password'):target['password']=camera['password']
            if target['enabled'] and not target['url']:raise ValueError(f'Bitte eine Adresse für Kamera {index+1} eintragen')
    return result


def public(value):
    result=copy.deepcopy(value)
    for camera in result['cameras']:
        camera['passwordSet']=bool(camera.pop('password',''))
    return result


def migrate(config,private):
    result=defaults(config.get('club'))
    try:
        old=json.loads((private/'cameras/go2rtc.json').read_text(encoding='utf-8'))
        for i,camera in enumerate(result['cameras'],1):
            source=old.get('streams',{}).get(f'table{i}','')
            if not isinstance(source,str):continue
            camera['transcode']=source.startswith('ffmpeg:')
            if camera['transcode']:source=source[len('ffmpeg:'):].split('#',1)[0]
            u=urlsplit(source)
            if u.username is not None or u.password is not None:continue
            camera['url']=rtsp_url(source);camera['enabled']=bool(camera['url'])
    except (OSError,ValueError,TypeError):pass
    return result


def camera_source(camera):
    u=urlsplit(rtsp_url(camera['url']))
    host=u.netloc
    if camera['username'] or camera['password']:
        host=quote(camera['username'],safe='')+':'+quote(camera['password'],safe='')+'@'+host
    source=urlunsplit((u.scheme,host,u.path,u.query,''))
    return 'ffmpeg:'+source+'#video=h264#width=1280#height=720' if camera['transcode'] else source


def state(data,source):
    """VIP projection; never changes the main display's source or match count."""
    if source!='web4sport' or data.get('status')!='ready':return data
    rows=data.get('matches',[])
    teams=data.get('teams') or {'home':'HEIM','away':'GAST'}
    score=data.get('team_score') or {'home':0,'away':0}
    game={'source':source,'id':str(data.get('sid','')),'competition':'TischtennisLive / Web4Sport',
          'completed':bool(rows) and all(m.get('finished') for m in rows)}
    boards=[];history=[]
    for i,row in enumerate(rows,1):
        sets=row.get('sets_won') or {'home':0,'away':0};finished=bool(row.get('finished'))
        one=[s.strip() for s in row.get('home','').split('/') if s.strip()]
        two=[s.strip() for s in row.get('away','').split('/') if s.strip()]
        label=f"{row.get('home_position','')}-{row.get('away_position','')}".strip('-')
        kind='Double' if str(row.get('home_position','')).startswith('D') else 'Single'
        started=finished or sum(sets.values())>0 or bool(row.get('set_scores'))
        boards.append({'active':not finished,'hasGame':True,'slot':i,'game':game,'teams':teams,'teamScore':score,
            'match':{'id':f"web4sport-{game['id']}-{row.get('number',i)}",'label':label,'type':kind,
                     'state':'Finished' if finished else 'InProgress' if started else 'Scheduled','setScores':row.get('set_scores',[])},
            'sideOne':{'players':one,'sets':sets['home'],'points':None},'sideTwo':{'players':two,'sets':sets['away'],'points':None}})
        if started:history.append({'slot':i,'label':label,'type':kind,'homePlayers':one,'awayPlayers':two,
                                  'homeSets':sets['home'],'awaySets':sets['away'],'finished':finished})
    return {**data,'scoreboards':boards,'history':history}


class Gateway:
    def __init__(self,private):
        self.folder=private/'cameras';self.signature=None
        self.status={'installed':False,'running':False,'message':'Lokaler Kameravermittler noch nicht eingerichtet.'}

    def sync(self,value):
        signature=json.dumps([{k:c[k] for k in ('enabled','url','username','password','transcode')} for c in value['cameras']],sort_keys=True)
        if signature==self.signature:return
        self.signature=signature
        binary=self.folder/'go2rtc_linux_amd64'
        ffmpegs=list((self.folder/'python/imageio_ffmpeg/binaries').glob('ffmpeg-linux*'))
        installed=sys.platform.startswith('linux') and binary.is_file() and bool(ffmpegs)
        self.status={'installed':installed,'running':False,'message':'Lokaler Kameravermittler noch nicht eingerichtet.'}
        if not installed:return
        active={f'table{i}':camera_source(c) for i,c in enumerate(value['cameras'],1) if c['enabled']}
        try:
            if not active:
                subprocess.run(['systemctl','--user','stop','tt-anzeigetafel-cameras.service'],check=True,timeout=10,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.status.update(message='Beide Kameras sind ausgeschaltet.');return
            settings={'api':{'listen':'127.0.0.1:1984'},'rtsp':{'listen':'127.0.0.1:8554'},'webrtc':{'listen':''},'log':{'level':'warn'},
                'preload':{name:'video' for name in active},'streams':active,
                'ffmpeg':{'bin':str(ffmpegs[0]),'h264':'-codec:v libx264 -g:v 30 -bf:v 0 -preset:v ultrafast -tune:v zerolatency -profile:v main -level:v 3.1 -threads:v 2 -r:v 15'}}
            target=self.folder/'go2rtc.json';temp=target.with_suffix('.tmp')
            temp.write_text(json.dumps(settings),encoding='utf-8');temp.chmod(0o600);temp.replace(target)
            subprocess.run(['systemctl','--user','restart','tt-anzeigetafel-cameras.service'],check=True,timeout=12,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.status.update(running=True,message='Kamerakonfiguration übernommen. Die Videobilder verbinden sich neu.')
        except (OSError,subprocess.SubprocessError):
            self.status.update(message='Kameravermittler konnte nicht neu gestartet werden. Linux-Dienst prüfen.')

    def info(self):
        result=copy.deepcopy(self.status)
        if result['installed'] and result['running']:
            try:
                with socket.create_connection(('127.0.0.1',1984),timeout=.25):pass
            except OSError:
                result.update(running=False,message='Kameravermittler startet oder ist nicht erreichbar.')
        return result
