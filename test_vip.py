"""VIP isolation, secret handling, source projection and gateway lifecycle."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import requests
import server
from public.support import vip,clicktt


class VipTests(unittest.TestCase):
    def test_independent_colors_and_secret_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            app=server.App(Path(directory));normal=copy.deepcopy(app.config['club'])
            app.update({'vip':{'colors':{'accent':'#123456'},'cameras':[{'enabled':True,'url':'rtsp://192.168.1.20/a','username':'camera','password':'private-camera-secret'},{}]}})
            self.assertEqual(app.config['club'],normal)
            restored=server.App(Path(directory))
            self.assertEqual(restored.config['vip']['colors']['accent'],'#123456')
            self.assertNotIn('private-camera-secret',json.dumps(restored.public_config()))
            self.assertTrue(restored.public_config()['vip']['cameras'][0]['passwordSet'])
            restored.update({'vip':{'cameras':[{'password':''},{}]}})
            self.assertEqual(restored.config['vip']['cameras'][0]['password'],'private-camera-secret')
            restored.update({'vip':{'cameras':[{'clearPassword':True},{}]}})
            self.assertFalse(restored.public_config()['vip']['cameras'][0]['passwordSet'])

    def test_invalid_patches_are_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            app=server.App(Path(directory));before=app.path.read_bytes()
            for value in [{'colors':{'accent':'red'}},{'colors':{'secret':'#000000'}},{'firstTable':True},
                          {'footer':{'clock':1}},{'footer':{'heightPercent':float('nan')}},
                          {'cameras':[{'enabled':True},{}]},{'cameras':[]}]:
                with self.subTest(value=value),self.assertRaises(ValueError):app.update({'vip':value})
                self.assertEqual(app.path.read_bytes(),before)

    def test_urls_and_credential_encoding(self):
        for url in ['file:///etc/passwd','http://192.168.1.1/','ffmpeg:exec:anything',
                    'rtsp://192.168.1.1/x#raw=bad','rtsp://user:password@192.168.1.1/x','rtsp://x/a\n']:
            with self.subTest(url=url),self.assertRaises(ValueError):vip.rtsp_url(url)
        c=vip.defaults()['cameras'][0];c.update(url='rtsp://192.168.1.10/stream1',username='name@room',password='p# &"')
        source=vip.camera_source(c)
        self.assertIn('name%40room:p%23%20%26%22@',source)
        self.assertTrue(source.endswith('#video=h264#width=1280#height=720'))

    def test_demo_migration_and_defaults_without_hardcoded_camera(self):
        self.assertTrue(all(not c['url'] and not c['enabled'] for c in vip.defaults()['cameras']))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'cameras').mkdir()
            (root/'cameras/go2rtc.json').write_text(json.dumps({'streams':{'table1':'ffmpeg:rtsp://192.168.1.10/a#video=h264','table2':'rtsp://192.168.1.11/b'}}))
            value=vip.migrate({'club':{'primary':'#abcdef','background':'#010203'}},root)
            self.assertEqual(value['colors']['accent'],'#abcdef')
            self.assertEqual(value['cameras'][0]['url'],'rtsp://192.168.1.10/a')
            self.assertTrue(all(c['enabled'] for c in value['cameras']))
            self.assertFalse(value['cameras'][1]['transcode'])

    def test_gateway_restarts_only_for_camera_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'cameras';(folder/'python/imageio_ffmpeg/binaries').mkdir(parents=True)
            (folder/'go2rtc_linux_amd64').touch();(folder/'python/imageio_ffmpeg/binaries/ffmpeg-linux-test').touch()
            gateway=vip.Gateway(root);value=vip.defaults();value['cameras'][0].update(enabled=True,url='rtsp://192.168.1.10/a')
            with patch('public.support.vip.sys.platform','linux'),patch('public.support.vip.subprocess.run') as run:
                gateway.sync(value);self.assertEqual(run.call_count,1)
                content=json.loads((folder/'go2rtc.json').read_text())
                self.assertEqual(content['api']['listen'],'127.0.0.1:1984')
                self.assertEqual(set(content['streams']),{'table1'})
                value['colors']['accent']='#123456';gateway.sync(value);self.assertEqual(run.call_count,1)
                value['cameras'][0]['label']='Neue Beschriftung';gateway.sync(value);self.assertEqual(run.call_count,1)
                value['cameras'][0]['url']='rtsp://192.168.1.10/b';gateway.sync(value);self.assertEqual(run.call_count,2)
                value['cameras'][0]['enabled']=False;gateway.sync(value);self.assertEqual(run.call_args.args[0][2],'stop')

    def test_web4sport_projection_has_sets_not_invented_points(self):
        data={'status':'ready','sid':'42','updated':'2026-11-16T10:00:00+01:00','teams':{'home':'Verein II','away':'Gast'},'team_score':{'home':1,'away':0},
              'matches':[{'number':1,'home':'Spieler A / Spieler B','away':'Spieler C / Spieler D','home_position':'D1','away_position':'D1',
                          'sets_won':{'home':3,'away':1},'set_scores':[{'home':11,'away':7}],'finished':True}]}
        before=copy.deepcopy(data);result=vip.state(data,'web4sport')
        self.assertEqual(data,before)
        self.assertEqual(result['scoreboards'][0]['match']['type'],'Double')
        self.assertIsNone(result['scoreboards'][0]['sideOne']['points'])
        self.assertTrue(result['scoreboards'][0]['game']['completed'])
        self.assertEqual(len(result['history']),1)

    def test_vip_api_does_not_apply_normal_match_count(self):
        with tempfile.TemporaryDirectory() as directory:
            app=server.App(Path(directory));app.update({'dataSource':'clicktt','display':{'mode':'detail','intervalSeconds':30,'web4sportMatchCount':1}})
            fixture=json.loads((Path(__file__).parent/'tests/fixtures/clicktt-15876082.json').read_text())
            app.publish(server.reader_key(app.config),'ready','test',payload=clicktt.normalize(fixture,'15876082',3))
            http=server.create_server(app,0);worker=threading.Thread(target=http.serve_forever,daemon=True);worker.start()
            try:
                base=f'http://127.0.0.1:{http.server_port}'
                self.assertEqual(len(requests.get(base+'/api/state',timeout=3).json()['scoreboards']),1)
                self.assertEqual(len(requests.get(base+'/api/vip/state',timeout=3).json()['scoreboards']),2)
                self.assertIn('colors',requests.get(base+'/api/vip',timeout=3).json()['config'])
            finally:http.shutdown();http.server_close();worker.join()


if __name__=='__main__':unittest.main()
