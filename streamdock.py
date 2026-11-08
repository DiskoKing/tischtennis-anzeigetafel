#!/usr/bin/env python3
"""Optional local MiraBox 293 V3 controls; stdlib only, no global keyboard capture."""
import argparse
import io
import json
import os
from pathlib import Path
import select
import sys
import time
import urllib.error
import urllib.request
import uuid

MAPPING = {1: ('home', 1), 2: ('home', -1), 4: ('away', 1), 5: ('away', -1)}
ASSETS = Path(__file__).with_name('public')/'assets/streamdock-icons'

def device_path():
    for entry in Path('/sys/class/hidraw').glob('hidraw*'):
        try:
            description = (entry/'device/uevent').read_text()
            if 'HID_ID=0003:00006603:00001006' in description and '/input0' in description:
                return '/dev/'+entry.name
        except OSError:
            continue
    return None

def send(fd, command):
    payload = b'\x00CRT\x00\x00'+command
    if len(payload)>1025:
        raise ValueError('Report too long')
    data=payload.ljust(1025,b'\0')
    if os.write(fd,data)!=len(data):
        raise OSError('Incomplete HID report')

def write_image(fd, slot, image):
    send(fd,b'BAT\0\0'+len(image).to_bytes(2,'big')+bytes([slot+1]))
    for start in range(0,len(image),1024):
        chunk=(b'\0'+image[start:start+1024]).ljust(1025,b'\0')
        if os.write(fd,chunk)!=1025:
            raise OSError('Incomplete image report')

def theme_signature(config):
    return tuple(config['club'].get(key,'') for key in ('logo','primary','name'))

def apply_theme(fd, client, config):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print('Für Dock-Vereinsdesign optional python3-pil installieren.',flush=True)
        for slot,name in ((10,'home-plus'),(11,'home-minus'),(13,'away-plus'),(14,'away-minus')):
            write_image(fd,slot,(ASSETS/(name+'.jpg')).read_bytes())
        send(fd,b'STP')
        return
    accent=config['club'].get('primary','#008e87')
    canvas=Image.new('RGB',(560,336),'#0b1119')
    draw=ImageDraw.Draw(canvas)
    try:
        small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',18)
        big=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',58)
    except OSError:
        small=ImageFont.load_default(size=18);big=ImageFont.load_default(size=58)
    draw.rounded_rectangle((173,120,387,331),radius=15,outline=accent,width=2)
    try:
        raw=client.image(config['club'].get('logo','assets/default-logo.svg'))
        logo=Image.open(io.BytesIO(raw))
        if logo.width>4096 or logo.height>4096:raise ValueError('Logo too large')
        logo=logo.convert('RGBA');logo.thumbnail((184,184))
        canvas.paste(logo,((560-logo.width)//2,128+(184-logo.height)//2),logo)
    except (OSError,ValueError):
        draw.text((280,185),'TT',font=big,anchor='mt',fill='white')
    for column,title,symbol in ((0,'HEIM','+'),(1,'HEIM','−'),(3,'GAST','+'),(4,'GAST','−')):
        x=column*112
        draw.rounded_rectangle((x+3,3,x+108,108),radius=12,fill='#121e29',outline=accent,width=3)
        draw.text((x+56,12),title,font=small,anchor='mt',fill='white')
        draw.text((x+56,32),symbol,font=big,anchor='mt',fill='white')
    for row in range(3):
        for column in range(5):
            tile=canvas.crop((column*112,row*112,(column+1)*112,(row+1)*112)).rotate(180)
            data=io.BytesIO();tile.save(data,format='JPEG',quality=90)
            write_image(fd,(2-row)*5+column,data.getvalue())
    send(fd,b'STP')

def initialize(fd, client):
    for command in (b'MOD\0\x003', b'DIS', b'LIG\0\0\x46', b'CONNECT'):
        send(fd,command)
    config=client.request('/api/config')
    apply_theme(fd,client,config)
    return theme_signature(config)

class Client:
    def __init__(self, url):
        self.url=url.rstrip('/')
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.token=None

    def request(self,path,body=None):
        if body is not None and not self.token:
            self.token=self.request('/api/session')['csrf']
        headers={'Content-Type':'application/json'}
        if body is not None:headers['X-Scoreboard-CSRF']=self.token
        request=urllib.request.Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
        try:
            with self.opener.open(request,timeout=2) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code==403:self.token=None
            raise

    def press(self,state,side,delta):
        action={'gameId':state['gameId'],'eventId':uuid.uuid4().hex,'side':side,'delta':delta}
        for attempt in range(2):
            try:return self.request('/api/manual',action)
            except (OSError,ValueError):
                if attempt:raise

    def image(self,path):
        if not path.startswith(('/api/logo','assets/')):raise ValueError('Unsupported logo path')
        with self.opener.open(self.url+'/'+path.lstrip('/'),timeout=2) as response:
            return response.read(10*1024*1024+1)

def run(client):
    path=device_path()
    if not path:return False
    fd=os.open(path,os.O_RDWR|os.O_NONBLOCK)
    try:
        theme=initialize(fd,client)
        held=set();state=None;next_state=0;keep=time.monotonic()+15
        next_theme=time.monotonic()+10
        # Discard buffered presses from before the daemon owned the device.
        arm_after=time.monotonic()+1.5
        print('Stream Dock verbunden: Heim +/-, frei, Gast +/- (obere Reihe).',flush=True)
        while True:
            now=time.monotonic()
            if now>=next_theme:
                try:
                    config=client.request('/api/config')
                    if theme_signature(config)!=theme:
                        apply_theme(fd,client,config);theme=theme_signature(config)
                except (OSError,ValueError):pass
                next_theme=time.monotonic()+10
            if now>=keep:send(fd,b'CONNECT');keep=now+15
            if now>=next_state:
                try:state=client.request('/api/manual')
                except (OSError,ValueError):state=None
                next_state=now+0.5
            if not select.select([fd],[],[],0.1)[0]:continue
            data=os.read(fd,512)
            if not data:raise OSError('Dock disconnected')
            if len(data)<11 or not data.startswith(b'ACK\0\0OK\0\0'):continue
            key,pressed=data[9:11]
            if pressed==0:held.discard(key);continue
            if pressed!=1 or key in held:continue
            held.add(key)
            if time.monotonic()<arm_after or not state or not state.get('enabled') or key not in MAPPING:continue
            try:state=client.press(state,*MAPPING[key])
            except (OSError,ValueError):
                state=None
                print('Zählaktion nicht bestätigt; Verbindung prüfen.',flush=True)
    finally:
        os.close(fd)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8081)
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Ungültiger Port')
    client=Client('http://127.0.0.1:'+str(args.port))
    while True:
        try:run(client)
        except (OSError,ValueError) as error:
            print('Dock nicht verfügbar ('+type(error).__name__+'); erneuter Versuch.',flush=True)
        time.sleep(3)

if __name__=='__main__':main()
