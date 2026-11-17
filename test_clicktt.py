import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import requests
import server
from public.support import clicktt

LINK='https://www.mytischtennis.de/click-tt/DTTB/26--27/ligen/2._Bundesliga/gruppe/518220/spielbericht/15876082/TTC_SR_Hohenstein-Ernstthal-vs-1._FC_K%C3%B6ln'


def fixture():
    return json.loads((Path(__file__).parent/'tests/fixtures/clicktt-15876082.json').read_text(encoding='utf-8'))


class Response:
    def __init__(self,body,status=200):
        self.content=body.encode() if isinstance(body,str) else body
        self.status_code=status
        self.is_redirect=300<=status<400
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def raise_for_status(self):
        if self.status_code>=400:raise requests.HTTPError(response=self)
    def iter_content(self,size):yield self.content


class ClickTTTests(unittest.TestCase):
    def test_public_report_link_whitelist_and_canonicalization(self):
        url,identity=clicktt.report_link(LINK+'?tracking=discard#fragment')
        self.assertEqual(url,LINK)
        self.assertEqual(identity,'15876082')
        for url in ['http://www.mytischtennis.de'+urlsplit_path(),LINK.replace('www.mytischtennis.de','127.0.0.1'),
                    LINK.replace('www.mytischtennis.de','www.mytischtennis.de.evil.test'),
                    LINK.replace('https://','https://user:password@'),LINK.replace('.de/','.de:8443/'),
                    'file:///etc/passwd',LINK.replace('/15876082/','/evil/'),LINK.replace('/15876082/','/%2f/'),LINK.replace('https://','https://\n')]:
            with self.subTest(url=url),self.assertRaises(ValueError):clicktt.report_link(url)

    def test_snapshot_names_total_and_live_points(self):
        result=clicktt.normalize(fixture(),'15876082')
        boards=result['scoreboards']
        self.assertEqual(len(boards),2)
        self.assertEqual(boards[0]['teams'],{'home':'TTC SR Hohenstein-Ernstthal','away':'1. FC Köln'})
        self.assertEqual(boards[0]['teamScore'],{'home':0,'away':4})
        self.assertEqual(boards[0]['game']['competition'],'2. Bundesliga Erwachsene')
        self.assertEqual(boards[0]['sideOne']['players'],['Miguel Nunez Tapia'])
        self.assertEqual(boards[0]['sideOne']['points'],10)
        self.assertEqual(boards[0]['sideTwo']['points'],10)
        self.assertEqual(boards[1]['sideTwo']['sets'],2)
        self.assertEqual(boards[1]['sideTwo']['points'],0)
        self.assertFalse(boards[0]['sideOne']['serving'])
        self.assertEqual(boards[0]['match']['label'],'3-4')
        self.assertTrue(boards[0]['match']['setScores'])
        self.assertEqual(boards[0]['match']['setScores'][-1],{'home':10,'away':10})
        self.assertNotIn('person_id',json.dumps(result))
        self.assertEqual(len(clicktt.normalize(fixture(),'15876082',1)['scoreboards']),1)
        self.assertEqual(len(result['history']),6)
        self.assertEqual(result['history'][0]['homeSets'],2)
        self.assertTrue(result['history'][0]['finished'])
        self.assertFalse(result['history'][-1]['finished'])
        self.assertNotIn('person_id',json.dumps(result['history']))

    def test_scheduled_finished_doubles_and_no_false_setball(self):
        data=fixture();data['is_completed']=True;data['matches_guest']=6
        result=clicktt.normalize(data,'15876082')['scoreboards'][0]
        self.assertFalse(result['active']);self.assertEqual(result['teamScore']['away'],6)
        self.assertEqual(result['match']['state'],'Finished')
        self.assertIn('sideOne',result)
        finished=[r for r in data['match'] if r.get('winner_is_home') is not None or r.get('matches_home') or r.get('matches_guest') or max(r.get('sets_home') or 0,r.get('sets_guest') or 0)>=3]
        self.assertEqual(result['match']['label'],finished[-2]['match_name'])
        row=copy.deepcopy(fixture()['match'][4]);row.update(sets_home=0,sets_guest=0,set1_home=0,set1_guest=0,set2_home=0,set2_guest=0)
        data=fixture();data['match']=[row]
        self.assertFalse(clicktt.normalize(data,'15876082')['scoreboards'][0]['active'])
        row.update(game_type='double',set1_home=11,set1_guest=9)
        row['mm_player12']={'firstname':'Zweiter','lastname':'Spieler'}
        result=clicktt.normalize(data,'15876082')['scoreboards'][0]
        self.assertEqual(result['sideOne']['points'],0)
        self.assertEqual(result['match']['type'],'Double')
        self.assertEqual(len(result['sideOne']['players']),2)
        row['home_wo']=True
        self.assertFalse(clicktt.normalize(data,'15876082')['scoreboards'][0]['active'])

    def test_read_uses_fixed_live_endpoint_no_redirect_or_credentials(self):
        session=Mock();session.get.return_value=Response(json.dumps({'data':fixture(),'error':None}))
        result=clicktt.read(session,LINK)
        self.assertEqual(result['scoreboards'][0]['game']['id'],'15876082')
        self.assertEqual(session.get.call_args.args[0],'https://www.mytischtennis.de/api/meeting/15876082/live')
        self.assertFalse(session.get.call_args.kwargs['allow_redirects'])
        session.get.return_value=Response('',302)
        with self.assertRaises(ValueError):clicktt.read(session,LINK)
        session.get.return_value=Response(b'x'*(clicktt.MAX_RESPONSE+1))
        with self.assertRaises(ValueError):clicktt.read(session,LINK)

    def test_safe_html_fallback_and_meeting_identity(self):
        context={'state':{'loaderData':{'routes/spielbericht.$meeting_id.$meeting_name':{'meetingId':'15876082','meetingReport':fixture()}}}}
        page='<script>window.__remixContext = '+json.dumps(context)+';</script><script>throw new Error()</script>'
        session=Mock();session.get.side_effect=[Response('',404),Response(page)]
        self.assertEqual(clicktt.read(session,LINK)['scoreboards'][0]['teamScore']['away'],4)
        self.assertEqual(session.get.call_args.args[0],LINK)
        with self.assertRaises(ValueError):clicktt.parse_page(page,'999')
        with self.assertRaises(ValueError):clicktt.parse_page('<script>window.__remixContext = alert(1)</script>','15876082')
        session.get.side_effect=[Response('',429)]
        with self.assertRaises(requests.HTTPError):clicktt.read(session,LINK)

    def test_configuration_migration_and_old_reader_cannot_publish(self):
        with tempfile.TemporaryDirectory() as folder:
            app=server.App(Path(folder))
            old=server.reader_key(app.config)
            app.update({'dataSource':'clicktt','clicktt':{'url':LINK}})
            self.assertEqual(server.App(Path(folder)).config['clicktt']['url'],LINK)
            key=server.reader_key(app.config)
            self.assertNotEqual(old,key)
            app.publish(old,'ready','old',payload={'scoreboards':[{'wrong':True}]})
            self.assertIsNone(app.payload)
            app.publish(key,'ready','click-TT',payload=clicktt.normalize(fixture(),'15876082'))
            self.assertEqual(app.get_data('clicktt')['scoreboards'][0]['teams']['away'],'1. FC Köln')
            app.update({'display':{'mode':'detail','intervalSeconds':30,'web4sportMatchCount':1}})
            self.assertEqual(len(app.get_data('clicktt')['scoreboards']),1)
            app.update({'clicktt':{'url':LINK.replace('15876082','15876083')}})
            self.assertIsNone(app.payload)
            with self.assertRaises(ValueError):app.manual_action({'side':'home','delta':1})

    def test_supervisor_uses_existing_worker_and_publish_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            app=server.App(Path(folder));app.update({'dataSource':'clicktt','clicktt':{'url':LINK}})
            def read(*args):
                app.stop.set();return clicktt.normalize(fixture(),'15876082')
            with patch.object(clicktt,'read',side_effect=read) as fetch,patch.object(server.requests,'Session'):
                app.supervise()
            fetch.assert_called_once()
            self.assertEqual(app.status,'ready')
            self.assertIsNotNone(app.last_success)


def urlsplit_path():
    from urllib.parse import urlsplit
    return urlsplit(LINK).path


if __name__=='__main__':unittest.main()
