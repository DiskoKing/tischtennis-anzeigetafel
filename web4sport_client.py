import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
BASE = "https://bericht.web4sport.de/default.aspx"

def url(said, sid, page):
    return f'{BASE}?Area=Report&SAID={said}&SID={sid}&SpielPage={page}&EingabeModus=0'


def login(session, username, password, said, sid):
    target = f'{BASE}?Area=Report'
    r = session.get(target, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    form = soup.find('form')
    if form is None:
        raise RuntimeError('Loginformular nicht gefunden')
    action = urljoin(r.url, form.get('action', ''))
    data = {}
    for field in form.find_all('input'):
        name = field.get('name')
        if name and field.get('type', '').lower() == 'hidden':
            data[name] = field.get('value', '')
    data.update(username=username, password=password, b_Cookie='on')
    r = session.post(action, data=data, headers={'Referer': target}, timeout=20)
    r.raise_for_status()
    if BeautifulSoup(r.text, 'html.parser').find('input', {'name': 'password'}):
        raise RuntimeError('Login fehlgeschlagen')



def read_teams(soup):
    # Use the heading of this report, never names cached from a previous SID.
    heading = soup.select_one('section[role="main"] h1 .shorten-long-text')
    names = re.split(r'\s+-vs-\s+', heading.get_text(' ', strip=True), maxsplit=1) if heading else []
    if len(names) != 2 or not all(name.strip() for name in names):
        print('Web4Sport: Mannschaftsnamen fehlen; neutrale Anzeige HEIM/GAST', flush=True)
        return {'home': '', 'away': ''}
    return {'home': names[0].strip(), 'away': names[1].strip()}


def read(session, said, sid):
    r = session.get(url(said, sid, 'Ergebnis'), timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    if soup.find('input', {'name': 'password'}):
        raise RuntimeError('Sitzung abgelaufen')

    def txt(name):
        e = soup.find(id=name)
        return e.get_text(' ', strip=True) if e else ''

    def val(name):
        e = soup.find(id=name)
        return str(e.get('value', '')) if e else ''

    matches = []
    for n in range(1, 30):
        home, away = txt(f'TD_SplA_{n}'), txt(f'TD_SplB_{n}')
        if not home or not away:
            continue
        scores = []
        for s in range(1, 6):
            a, b = val(f'Sp_{n}_Sa_{s}_A'), val(f'Sp_{n}_Sa_{s}_B')
            if a.isdigit() and b.isdigit() and (int(a) > 0 or int(b) > 0):
                scores.append({'set': s, 'home': int(a), 'away': int(b)})
        a, b = val(f'Sp_{n}_Satz_A'), val(f'Sp_{n}_Satz_B')
        a, b = int(a) if a.isdigit() else 0, int(b) if b.isdigit() else 0
        matches.append({
            'number': n, 'home': home, 'away': away,
            'home_position': txt(f'TD_PosA_{n}'),
            'away_position': txt(f'TD_PosB_{n}'),
            'sets_won': {'home': a, 'away': b},
            'set_scores': scores,
            'finished': max(a, b) >= 3,
        })
    if not matches:
        raise RuntimeError('Keine Begegnungen gefunden; JSON bleibt unverändert')
    return matches, read_teams(soup)


