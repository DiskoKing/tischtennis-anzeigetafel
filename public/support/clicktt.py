"""Public myTischtennis/click-TT reports; the same read-only live endpoint as the site."""
from datetime import datetime
import json
import re
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import requests

ORIGIN = 'https://www.mytischtennis.de'
MAX_RESPONSE = 2 * 1024 * 1024


def report_link(value):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c)<32 for c in value):
        raise ValueError('Bitte einen myTischtennis/click-TT-Spielbericht-Link eintragen.')
    try:
        url = urlsplit(value.strip())
        path = unquote(url.path)
        match = re.fullmatch(r'/click-tt/[A-Za-z0-9_-]+/\d{2}--\d{2}/ligen/[^/\x00-\x20]+/gruppe/\d{1,12}/spielbericht/(\d{1,12})/[^/\x00-\x20]+/?', path)
        if (url.scheme != 'https' or url.hostname not in ('mytischtennis.de','www.mytischtennis.de') or
                url.username is not None or url.password is not None or url.port not in (None,443) or not match):
            raise ValueError()
        return urlunsplit(('https','www.mytischtennis.de',quote(path.rstrip('/'),safe='/-._~'),'','')), match[1]
    except ValueError:
        raise ValueError('Bitte den vollständigen HTTPS-Spielbericht-Link von myTischtennis.de verwenden.') from None


def number(value, maximum=99):
    if value is None: return 0
    if isinstance(value, bool) or not re.fullmatch(r'\d{1,3}',str(value)) or not 0 <= int(value) <= maximum:
        raise ValueError('Unerwarteter Zahlenwert im click-TT-Spielbericht.')
    return int(value)


def text(value, required=False):
    if not isinstance(value,str) or not value.strip() or len(value)>200:
        if required: raise ValueError('Mannschaftsnamen fehlen im click-TT-Spielbericht.')
        return ''
    return ' '.join(value.split())


def players(row, side):
    names=[]
    for slot in (1,2):
        player=row.get(f'mm_player{side}{slot}')
        if isinstance(player,dict):
            name=' '.join(filter(None,(text(player.get('firstname')),text(player.get('lastname')))))
            if name:names.append(name)
    return names


def normalize(report, meeting_id, limit=2):
    if not isinstance(report,dict) or not isinstance(report.get('match'),list) or len(report['match'])>100:
        raise ValueError('click-TT-Spielbericht hat ein unbekanntes Format.')
    teams={'home':text(report.get('team_home'),True),'away':text(report.get('team_guest'),True)}
    rows=report['match']
    completed=report.get('is_completed') is True or bool(report.get('end_date'))
    score = ({'home':number(report.get('matches_home')), 'away':number(report.get('matches_guest'))} if completed or not rows else
             {side:sum(number(r.get('matches_'+key)) for r in rows if isinstance(r,dict)) for side,key in (('home','home'),('away','guest'))})
    game={'source':'clicktt','id':str(meeting_id),'competition':text(report.get('group_name')) or 'CLICK-TT',
          'startedAt':text(report.get('start_date')),'season':text(report.get('season_nickname')),'completed':completed}
    boards=[]
    finished_boards=[]
    history=[]
    for index,row in enumerate(rows):
        if not isinstance(row,dict): raise ValueError('Paarung im click-TT-Spielbericht ungültig.')
        home_sets,away_sets=number(row.get('sets_home'),7),number(row.get('sets_guest'),7)
        finished=(row.get('winner_is_home') is not None or number(row.get('matches_home'))>0 or
                  number(row.get('matches_guest'))>0 or max(home_sets,away_sets)>=3 or
                  row.get('home_wo') is True or row.get('guest_wo') is True)
        scores=[(number(row.get(f'set{i}_home')),number(row.get(f'set{i}_guest'))) for i in range(1,8) if f'set{i}_home' in row or f'set{i}_guest' in row]
        started=home_sets+away_sets>0 or any(a+b for a,b in scores)
        if not started: continue
        # Published set totals say which set is current. A just-completed set is
        # never reused as the next set's live ball score.
        set_index=home_sets+away_sets
        a,b=scores[set_index] if set_index<len(scores) else (0,0)
        if max(a,b)>=11 and abs(a-b)>=2:a,b=0,0
        one,two=players(row,1),players(row,2)
        if not one or not two: continue
        history.append({'slot':index+1,'label':text(row.get('match_name')),'type':'Double' if row.get('game_type')=='double' else 'Single',
                        'homePlayers':one,'awayPlayers':two,'homeSets':home_sets,'awaySets':away_sets,'finished':finished})
        target=finished_boards if finished else boards
        target.append({'active':not finished,'hasGame':True,'slot':index+1,'game':game,'teams':teams,'teamScore':score,
                       'match':{'id':'clicktt-'+str(meeting_id)+'-'+str(row.get('match_uuid') or index+1),
                                'state':'Finished' if finished else 'InProgress','type':'Double' if row.get('game_type')=='double' else 'Single',
                                'label':text(row.get('match_name')),
                                'setScores':[{'home':a,'away':b} for a,b in scores if a+b>0]},
                       'sideOne':{'players':one,'sets':home_sets,'points':a,'serving':False},
                       'sideTwo':{'players':two,'sets':away_sets,'points':b,'serving':False}})
    boards=boards[:limit] if not completed else []
    if not boards and finished_boards:
        boards=finished_boards[-limit:]
    if not boards:
        boards=[{'active':False,'hasGame':True,'slot':1,'game':game,'teams':teams,'teamScore':score,
                 'match':{'id':'clicktt-'+str(meeting_id)+'-summary','state':'Finished' if completed else 'Scheduled','type':'Single'}}]
    return {'source':'clicktt','updated':datetime.now().astimezone().isoformat(),'scoreboards':boards,'history':history}


def body(session, url):
    # URLs are constructed on a fixed public origin. Never follow redirects to
    # arbitrary hosts; never execute the site's JS or send stored login cookies.
    with session.get(url,timeout=(8,20),allow_redirects=False,stream=True) as response:
        response.raise_for_status()
        if response.is_redirect:raise ValueError('click-TT hat den Spielbericht umgeleitet. Bitte Link prüfen.')
        data=bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data)>MAX_RESPONSE:raise ValueError('click-TT-Antwort ist zu groß.')
        return bytes(data).decode('utf-8-sig')


def parse_page(html, meeting_id):
    marker=re.search(r'window\.__remixContext\s*=\s*',html)
    if not marker:raise ValueError('Öffentlicher click-TT-Spielbericht nicht erkannt.')
    try:
        context=json.JSONDecoder().raw_decode(html[marker.end():])[0]
        loaders=context['state']['loaderData']
        for key,data in loaders.items():
            if 'spielbericht.' in key and isinstance(data,dict) and str(data.get('meetingId'))==meeting_id:
                return data['meetingReport']
    except (KeyError,TypeError,AttributeError,json.JSONDecodeError): pass
    raise ValueError('Spielbericht-ID stimmt nicht oder click-TT-Daten fehlen.')


def read(session, link, limit=2):
    url,identity=report_link(link)
    try:
        result=json.loads(body(session,ORIGIN+'/api/meeting/'+identity+'/live'))
    except requests.HTTPError as error:
        if error.response is None or error.response.status_code!=404:raise
        result=None
    if result is None or (isinstance(result,dict) and not result.get('data')):
        report=parse_page(body(session,url),identity)
    elif not isinstance(result,dict) or result.get('error'):
        raise ValueError('click-TT meldet einen Fehler beim Laden der Live-Daten.')
    else: report=result['data']
    return normalize(report,identity,limit)
