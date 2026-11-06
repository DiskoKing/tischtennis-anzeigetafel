import json
import sys
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


# ==================================================
# KONFIGURATION
# ==================================================

PROJECT_ID = "janova-99680"
REFEREE_ID = os.environ.get("JANOVA_REFEREE_ID", "")

POLL_SECONDS = 1.0
TEAM_SCORE_REFRESH_SECONDS = 5.0
REFEREE_REFRESH_SECONDS = 60.0
ACTIVE_MATCH_REDISCOVER_SECONDS = 30.0
SCOREBOARD_COUNT = 3

OUTPUT_COMBINED = "scoreboards.json"

FIRESTORE_ROOT = (
    f"https://firestore.googleapis.com/v1/"
    f"projects/{PROJECT_ID}/databases/(default)/documents"
)

REFEREE_URL = (
    f"{FIRESTORE_ROOT}/referees/{REFEREE_ID}"
)

MATCHES_URL = (
    f"{REFEREE_URL}/scoredMatches"
)

RUN_QUERY_URL = (
    f"{REFEREE_URL}:runQuery"
)


# ==================================================
# LAUFZEIT-CACHE
# ==================================================

team_score_cache = {}
team_score_last_refresh = {}

previous_slots = {}

# Letzte bekannte Mannschaftspartie pro Zählgerät.
# Bleibt auch erhalten, wenn gerade kein Match läuft.
last_game_by_slot = {}

run_query_available = True

fallback_documents_this_cycle = None

# Referee/installIds ändern sich im laufenden Spielbetrieb praktisch nie.
# Deshalb nicht bei jedem Punkt erneut aus dem Internet laden.
cached_slots = None
referee_last_refresh = 0.0

# Sobald ein laufendes Match gefunden wurde, kennen wir dessen Dokument-ID.
# Danach laden wir genau dieses Dokument direkt, statt jede Sekunde erneut runQuery zu bemühen.
# Sicherheitsnetz: spätestens alle ACTIVE_MATCH_REDISCOVER_SECONDS wird trotzdem neu gesucht.
active_document_by_install = {}
active_document_last_search = {}


# ==================================================
# FIRESTORE AUSPACKEN
# ==================================================

def firestore_value(value):

    if not isinstance(value, dict):
        return None

    if "stringValue" in value:
        return value["stringValue"]

    if "integerValue" in value:
        return int(value["integerValue"])

    if "doubleValue" in value:
        return float(value["doubleValue"])

    if "booleanValue" in value:
        return value["booleanValue"]

    if "timestampValue" in value:
        return value["timestampValue"]

    if "nullValue" in value:
        return None

    if "mapValue" in value:

        fields = value["mapValue"].get(
            "fields",
            {}
        )

        return {
            key: firestore_value(val)
            for key, val in fields.items()
        }

    if "arrayValue" in value:

        values = value["arrayValue"].get(
            "values",
            []
        )

        return [
            firestore_value(item)
            for item in values
        ]

    return None


def unpack_fields(fields):

    return {
        key: firestore_value(value)
        for key, value in fields.items()
    }


def unpack_document(document):

    return {

        "id": (
            document
            .get("name", "")
            .split("/")[-1]
        ),

        "fields": unpack_fields(
            document.get(
                "fields",
                {}
            )
        ),

        "createTime": document.get(
            "createTime",
            ""
        ),

        "updateTime": document.get(
            "updateTime",
            ""
        )
    }


# ==================================================
# HTTP
# ==================================================

def http_json(
    url,
    method="GET",
    payload=None
):

    data = None

    headers = {
        "Accept": "application/json"
    }

    if payload is not None:

        data = json.dumps(
            payload
        ).encode("utf-8")

        headers[
            "Content-Type"
        ] = "application/json"


    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=headers
    )


    with urllib.request.urlopen(
        request,
        timeout=2
    ) as response:

        return json.loads(
            response
            .read()
            .decode("utf-8")
        )


def load_document(url):

    document = http_json(
        url
    )

    return unpack_document(
        document
    )


# ==================================================
# FIRESTORE RUNQUERY
# ==================================================

def run_query_equal(
    field_path,
    value
):

    global run_query_available


    if not run_query_available:
        return None


    payload = {

        "structuredQuery": {

            "from": [
                {
                    "collectionId":
                        "scoredMatches"
                }
            ],

            "where": {

                "fieldFilter": {

                    "field": {
                        "fieldPath":
                            field_path
                    },

                    "op":
                        "EQUAL",

                    "value": {
                        "stringValue":
                            str(value)
                    }
                }
            }
        }
    }


    try:

        result = http_json(
            RUN_QUERY_URL,
            method="POST",
            payload=payload
        )


        documents = []


        for item in result:

            document = item.get(
                "document"
            )

            if document:

                documents.append(
                    unpack_document(
                        document
                    )
                )


        return documents


    except urllib.error.HTTPError as error:

        print()
        print(
            "runQuery nicht verfügbar."
        )

        print(
            "Wechsle auf Listen-Fallback."
        )

        print(
            "HTTP:",
            error.code
        )

        run_query_available = False

        return None


# ==================================================
# FALLBACK:
# ALLE MATCHES LADEN
# ==================================================

def load_all_matches():

    global fallback_documents_this_cycle


    if fallback_documents_this_cycle is not None:

        return fallback_documents_this_cycle


    documents = []

    page_token = None


    while True:

        params = {
            "pageSize": 100
        }


        if page_token:

            params[
                "pageToken"
            ] = page_token


        url = (
            MATCHES_URL
            + "?"
            + urllib.parse.urlencode(
                params
            )
        )


        data = http_json(
            url
        )


        for document in data.get(
            "documents",
            []
        ):

            documents.append(
                unpack_document(
                    document
                )
            )


        page_token = data.get(
            "nextPageToken"
        )


        if not page_token:
            break


    fallback_documents_this_cycle = (
        documents
    )

    return documents


# ==================================================
# DOKUMENTE NACH FELD FINDEN
# ==================================================

def find_documents_equal(
    field_path,
    value
):

    result = run_query_equal(
        field_path,
        value
    )


    if result is not None:
        return result


    documents = load_all_matches()

    parts = field_path.split(".")

    matches = []


    for document in documents:

        current = document[
            "fields"
        ]


        for part in parts:

            if not isinstance(
                current,
                dict
            ):

                current = None
                break


            current = current.get(
                part
            )


        if str(current) == str(value):

            matches.append(
                document
            )


    return matches


# ==================================================
# SPIELERNAMEN
# ==================================================

def player_name(player):

    if not isinstance(
        player,
        dict
    ):
        return None


    first = (
        player.get(
            "firstName",
            ""
        )
        or ""
    ).strip()


    last = (
        player.get(
            "lastName",
            ""
        )
        or ""
    ).strip()


    if (
        first
        and last
        and first.lower()
        != last.lower()
    ):

        return (
            f"{first} {last}"
        )


    return (
        first
        or last
        or None
    )


def read_team(team):

    if not isinstance(
        team,
        dict
    ):

        return {
            "type": "Unknown",
            "players": []
        }


    team_type = team.get(
        "type",
        "Single"
    )


    if team_type == "Double":

        players = [

            player_name(
                team.get(
                    "playerOne"
                )
            ),

            player_name(
                team.get(
                    "playerTwo"
                )
            )
        ]


    else:

        players = [

            player_name(
                team.get(
                    "player"
                )
            )
        ]


    players = [
        player
        for player in players
        if player
    ]


    return {
        "type": team_type,
        "players": players
    }


# ==================================================
# SPIELKONTEXT
# ==================================================

def detect_game_context(fields):

    janova_data = fields.get(
        "janovaMatchData"
    )


    if isinstance(
        janova_data,
        dict
    ):

        game_data = janova_data.get(
            "gameData"
        )


        if isinstance(
            game_data,
            dict
        ):

            game_id = game_data.get(
                "id"
            )


            if game_id:

                return {

                    "source":
                        "janova",

                    "gameId":
                        str(game_id),

                    "homeTeam":
                        str(
                            game_data.get(
                                "homeTeamName",
                                "Home"
                            )
                            or "Home"
                        ).strip(),

                    "awayTeam":
                        str(
                            game_data.get(
                                "awayTeamName",
                                "Away"
                            )
                            or "Away"
                        ).strip()
                }


    ttlive_data = fields.get(
        "ttliveData"
    )


    if isinstance(
        ttlive_data,
        dict
    ):

        ttlive_game = ttlive_data.get(
            "game"
        )


        if isinstance(
            ttlive_game,
            dict
        ):

            game_id = ttlive_game.get(
                "id"
            )


            if game_id:

                return {

                    "source":
                        "ttlive",

                    "gameId":
                        str(game_id),

                    "homeTeam":
                        str(
                            ttlive_game.get(
                                "home",
                                "Home"
                            )
                            or "Home"
                        ).strip(),

                    "awayTeam":
                        str(
                            ttlive_game.get(
                                "guest",
                                "Away"
                            )
                            or "Away"
                        ).strip()
                }


    return {

        "source":
            "unknown",

        "gameId":
            None,

        "homeTeam":
            "Home",

        "awayTeam":
            "Away"
    }


# ==================================================
# AKTUELLES MATCH EINES GERÄTS
# ==================================================

def find_active_match(
    install_id
):

    documents = find_documents_equal(
        "deviceInfo.installId",
        install_id
    )


    candidates = []


    for document in documents:

        fields = document[
            "fields"
        ]


        match_state = fields.get(
            "matchState",
            {}
        )


        if not isinstance(
            match_state,
            dict
        ):
            continue


        if (
            match_state.get(
                "state"
            )
            != "InProgress"
        ):
            continue


        updated = (
            fields.get(
                "lastUpdated"
            )
            or document.get(
                "updateTime",
                ""
            )
        )


        # Ein echtes Janova/TTLive-Match mit auflösbarer gameId ist
        # vertrauenswürdiger als ein altes/halbes InProgress-Dokument.
        context = detect_game_context(fields)
        has_game_context = bool(context.get("gameId"))

        candidates.append({

            "document":
                document,

            "updated":
                updated or "",

            "hasGameContext":
                has_game_context
        })


    if not candidates:
        return None


    # Erst gültiger Spielkontext, dann jüngstes Dokument.
    # Damit gewinnt ein echter aktueller Match gegen herumliegende
    # InProgress-Geisterdokumente ohne gameId.
    candidates.sort(
        key=lambda item: (
            item["hasGameContext"],
            item["updated"]
        ),
        reverse=True
    )


    return candidates[0][
        "document"
    ]


# ==================================================
# MATCH ALS MANNSCHAFTSPUNKT WERTEN
# ==================================================
# SCHNELLPFAD FÜR LAUFENDE MATCHES
# ==================================================

def find_active_match_fast(install_id):

    now = time.monotonic()
    known_id = active_document_by_install.get(install_id)
    last_search = active_document_last_search.get(install_id, 0.0)

    force_rediscover = (
        now - last_search >= ACTIVE_MATCH_REDISCOVER_SECONDS
    )

    # Schnellpfad: bekannte Dokument-ID direkt laden.
    # Aber nicht endlos daran festhalten: alle 30 Sekunden wird bewusst
    # neu gesucht, und Dokumente ohne echten Spielkontext werden verworfen.
    if known_id and not force_rediscover:
        try:
            document = load_document(
                f"{MATCHES_URL}/{urllib.parse.quote(str(known_id), safe='')}"
            )

            fields = document.get("fields", {})
            state = fields.get("matchState", {})
            device_info = fields.get("deviceInfo", {})
            context = detect_game_context(fields)

            if (
                isinstance(state, dict)
                and state.get("state") == "InProgress"
                and isinstance(device_info, dict)
                and str(device_info.get("installId")) == str(install_id)
                and context.get("gameId")
            ):
                return document

        except Exception:
            # Dokument beendet/kurz nicht erreichbar: normale Suche übernimmt.
            pass

        active_document_by_install.pop(install_id, None)

    # Reguläre Neusuche. Sie läuft beim ersten Zugriff, nach einem
    # ungültigen Cache-Treffer und spätestens alle 30 Sekunden.
    document = find_active_match(install_id)
    active_document_last_search[install_id] = now

    if document:
        context = detect_game_context(document.get("fields", {}))

        if context.get("gameId"):
            active_document_by_install[install_id] = document["id"]
        else:
            # Unvollständige InProgress-Dokumente niemals dauerhaft cachen.
            active_document_by_install.pop(install_id, None)
    else:
        active_document_by_install.pop(install_id, None)

    return document


def load_slots_cached():

    global cached_slots, referee_last_refresh

    now = time.monotonic()

    if (
        cached_slots is not None
        and now - referee_last_refresh < REFEREE_REFRESH_SECONDS
    ):
        return cached_slots

    referee_document = load_document(REFEREE_URL)
    referee = referee_document["fields"]
    install_ids = referee.get("installIds", [])

    if not isinstance(install_ids, list):
        install_ids = []

    slots = []
    for index in range(SCOREBOARD_COUNT):
        install_id = install_ids[index] if index < len(install_ids) else None
        slots.append({"slot": index + 1, "installId": install_id})

    cached_slots = slots
    referee_last_refresh = now
    return slots


# ==================================================

def get_match_winner(fields):

    score = fields.get(
        "score",
        {}
    )


    if not isinstance(
        score,
        dict
    ):
        return None


    sets_one = score.get(
        "playerOne",
        0
    )

    sets_two = score.get(
        "playerTwo",
        0
    )


    match_state = fields.get(
        "matchState",
        {}
    )


    if not isinstance(
        match_state,
        dict
    ):
        return None


    if (
        match_state.get(
            "state"
        )
        != "Ended"
    ):
        return None


    if fields.get(
        "currentSet"
    ) is not None:

        return None


    if (
        sets_one == 3
        and sets_two < 3
    ):

        return "home"


    if (
        sets_two == 3
        and sets_one < 3
    ):

        return "away"


    return None


# ==================================================
# MANNSCHAFTSSTAND BERECHNEN
# ==================================================

def calculate_team_score(
    context
):

    source = context[
        "source"
    ]

    game_id = context[
        "gameId"
    ]


    if not game_id:

        return {

            "home": 0,
            "away": 0,

            "matchesFound": 0,
            "matchesCounted": 0,

            "source":
                "unavailable"
        }


    if source == "janova":

        field_path = (
            "janovaMatchData."
            "gameData.id"
        )


    elif source == "ttlive":

        field_path = (
            "ttliveData.game.id"
        )


    else:

        return {

            "home": 0,
            "away": 0,

            "matchesFound": 0,
            "matchesCounted": 0,

            "source":
                "unavailable"
        }


    documents = find_documents_equal(
        field_path,
        game_id
    )


    home_score = 0
    away_score = 0
    counted = 0


    for document in documents:

        winner = get_match_winner(
            document[
                "fields"
            ]
        )


        if winner == "home":

            home_score += 1
            counted += 1


        elif winner == "away":

            away_score += 1
            counted += 1


    return {

        "home":
            home_score,

        "away":
            away_score,

        "matchesFound":
            len(documents),

        "matchesCounted":
            counted,

        "source":
            "janova-calculated"
    }


# ==================================================
# SCOREBOARD-DATEN BAUEN
# ==================================================

def build_scoreboard(
    slot,
    install_id,
    document
):

    # ----------------------------------------------
    # KEIN AKTUELLES MATCH
    # ----------------------------------------------

    if document is None:

        remembered_context = (
            last_game_by_slot.get(
                slot
            )
        )


        # Auf diesem Slot wurde bislang
        # noch keine Mannschaftspartie gesehen.

        if not remembered_context:

            return {

                "slot":
                    slot,

                "active":
                    False,

                "hasGame":
                    False,

                "updated":
                    datetime.now()
                    .isoformat(
                        timespec="seconds"
                    )
            }


        key = (

            remembered_context[
                "source"
            ],

            remembered_context[
                "gameId"
            ]
        )


        team_score = (
            team_score_cache.get(
                key,
                {
                    "home": 0,
                    "away": 0,
                    "matchesFound": 0,
                    "matchesCounted": 0,
                    "source":
                        "not-calculated"
                }
            )
        )


        return {

            "slot":
                slot,

            "active":
                False,

            "hasGame":
                True,

            "updated":
                datetime.now()
                .isoformat(
                    timespec="seconds"
                ),

            "game": {

                "source":
                    remembered_context[
                        "source"
                    ],

                "id":
                    remembered_context[
                        "gameId"
                    ]
            },

            "teams": {

                "home":
                    remembered_context[
                        "homeTeam"
                    ],

                "away":
                    remembered_context[
                        "awayTeam"
                    ]
            },

            "teamScore":
                team_score
        }


    # ----------------------------------------------
    # AKTUELLES MATCH VORHANDEN
    # ----------------------------------------------

    fields = document[
        "fields"
    ]


    context = detect_game_context(
        fields
    )


    team_one = read_team(
        fields.get(
            "teamOne",
            {}
        )
    )

    team_two = read_team(
        fields.get(
            "teamTwo",
            {}
        )
    )


    score = fields.get(
        "score",
        {}
    )

    if not isinstance(
        score,
        dict
    ):
        score = {}


    points = fields.get(
        "pointsCurrentSet",
        {}
    )

    if not isinstance(
        points,
        dict
    ):
        points = {}


    current_set = fields.get(
        "currentSet",
        {}
    )

    if not isinstance(
        current_set,
        dict
    ):
        current_set = {}


    serving_player = current_set.get(
        "servingPlayer"
    )


    state_data = fields.get(
        "matchState",
        {}
    )

    if not isinstance(
        state_data,
        dict
    ):
        state_data = {}


    key = (
        context["source"],
        context["gameId"]
    )


    team_score = (
        team_score_cache.get(
            key,
            {
                "home": 0,
                "away": 0,
                "matchesFound": 0,
                "matchesCounted": 0,
                "source":
                    "not-calculated"
            }
        )
    )


    return {

        "slot":
            slot,

        "active":
            True,

        "hasGame":
            True,

        "updated":
            datetime.now()
            .isoformat(
                timespec="seconds"
            ),

        "match": {

            "id":
                document["id"],

            "state":
                state_data.get(
                    "state",
                    "Unknown"
                ),

            "type":
                team_one["type"]
        },

        "game": {

            "source":
                context["source"],

            "id":
                context["gameId"]
        },

        "teams": {

            "home":
                context[
                    "homeTeam"
                ],

            "away":
                context[
                    "awayTeam"
                ]
        },

        "teamScore":
            team_score,

        "sideOne": {

            "players":
                team_one[
                    "players"
                ],

            "sets":
                score.get(
                    "playerOne",
                    0
                ),

            "points":
                points.get(
                    "playerOne",
                    0
                ),

            "serving":
                (
                    serving_player
                    == "Player.one"
                )
        },

        "sideTwo": {

            "players":
                team_two[
                    "players"
                ],

            "sets":
                score.get(
                    "playerTwo",
                    0
                ),

            "points":
                points.get(
                    "playerTwo",
                    0
                ),

            "serving":
                (
                    serving_player
                    == "Player.two"
                )
        }
    }


# ==================================================
# JSON ATOMAR SCHREIBEN
# ==================================================

def write_json_atomic(
    filename,
    data
):

    temp = (
        filename
        + ".tmp"
    )


    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


    os.replace(
        temp,
        filename
    )


# ==================================================
# KONSOLE
# ==================================================

def display_players(players):

    if not players:
        return "?"

    return " / ".join(
        name.upper()
        for name in players
    )


def print_status(
    scoreboards
):

    # A background reader has no interactive terminal. In particular, os.system
    # would launch a new cmd.exe for every polling cycle on Windows.
    if sys.stdout is None or not sys.stdout.isatty():
        return
    # Terminal escape sequences clear an interactive display without a child shell.
    sys.stdout.write("\033[2J\033[H")


    print(
        "=============================================="
    )

    print(
        "       TTSV LIVE READER  |  1 SEKUNDE"
    )

    print(
        "=============================================="
    )

    print()


    for scoreboard in scoreboards:

        slot = scoreboard[
            "slot"
        ]


        if not scoreboard.get(
            "hasGame"
        ):

            print(
                f"Zählgerät {slot}: "
                f"keine bekannte Partie"
            )

            print()
            continue


        teams = scoreboard[
            "teams"
        ]

        team_score = scoreboard[
            "teamScore"
        ]


        if scoreboard[
            "active"
        ]:

            print(
                f"Zählgerät {slot} | LIVE"
            )

        else:

            print(
                f"Zählgerät {slot} | PAUSE / KEIN MATCH"
            )


        print(
            f"{teams['home']} "
            f"{team_score['home']} : "
            f"{team_score['away']} "
            f"{teams['away']}"
        )


        if scoreboard[
            "active"
        ]:

            one = scoreboard[
                "sideOne"
            ]

            two = scoreboard[
                "sideTwo"
            ]


            serve_one = (
                " ●"
                if one["serving"]
                else ""
            )

            serve_two = (
                " ●"
                if two["serving"]
                else ""
            )


            print(
                f"  "
                f"{display_players(one['players']):28}"
                f"  Sätze {one['sets']}  "
                f"Punkte {one['points']}"
                f"{serve_one}"
            )


            print(
                f"  "
                f"{display_players(two['players']):28}"
                f"  Sätze {two['sets']}  "
                f"Punkte {two['points']}"
                f"{serve_two}"
            )


        print()


    print(
        "JSON aktualisiert:",
        datetime.now().strftime(
            "%H:%M:%S"
        )
    )

    print()

    print(
        "Teamstand-Prüfung spätestens alle:",
        TEAM_SCORE_REFRESH_SECONDS,
        "Sekunden"
    )

    print()

    print(
        "Beenden mit Strg+C"
    )


# ==================================================
# HAUPTSCHLEIFE
# ==================================================

print()
print(
    "Live-Reader startet ..."
)

print(
    "Punkte-Abfrage:",
    POLL_SECONDS,
    "Sekunde(n)"
)

print(
    "Teamstand-Abfrage:",
    TEAM_SCORE_REFRESH_SECONDS,
    "Sekunde(n)"
)

print()


while True:

    started = time.monotonic()

    fallback_documents_this_cycle = None


    try:

        # ==========================================
        # REFEREE / INSTALL-IDS (60-Sekunden-CACHE)
        # ==========================================

        slots = load_slots_cached()

        # ==========================================
        # AKTUELLE MATCHES
        # ==========================================

        current_documents = {}

        # Die drei Geräte parallel statt nacheinander abfragen.
        # Dadurch addieren sich die Firestore-Latenzen nicht mehr.
        jobs = {}
        with ThreadPoolExecutor(max_workers=max(1, SCOREBOARD_COUNT)) as executor:
            for slot in slots:
                number = slot["slot"]
                install_id = slot["installId"]

                if not install_id:
                    current_documents[number] = None
                    continue

                future = executor.submit(find_active_match_fast, install_id)
                jobs[future] = number

            for future in as_completed(jobs):
                number = jobs[future]
                current_documents[number] = future.result()


        # ==========================================
        # GAME-KONTEXTE SAMMELN
        # ==========================================

        active_contexts = {}


        for slot in slots:

            number = slot[
                "slot"
            ]

            document = (
                current_documents[
                    number
                ]
            )


            previous = previous_slots.get(
                number
            )


            current_match_id = (
                document["id"]
                if document
                else None
            )


            previous_match_id = (
                previous.get(
                    "matchId"
                )
                if previous
                else None
            )


            context = None


            # --------------------------------------
            # AKTUELLES MATCH VORHANDEN
            # --------------------------------------

            if document:

                context = detect_game_context(
                    document[
                        "fields"
                    ]
                )


                if context.get(
                    "gameId"
                ):

                    key = (

                        context[
                            "source"
                        ],

                        context[
                            "gameId"
                        ]
                    )


                    active_contexts[
                        key
                    ] = context


                    # Für diesen Slot merken.
                    last_game_by_slot[
                        number
                    ] = context


            # --------------------------------------
            # KEIN AKTUELLES MATCH
            #
            # Pause oder Match gerade beendet.
            # Letzte bekannte Partie weiter prüfen.
            # --------------------------------------

            else:

                remembered_context = (
                    last_game_by_slot.get(
                        number
                    )
                )


                if (
                    remembered_context
                    and
                    remembered_context.get(
                        "gameId"
                    )
                ):

                    key = (

                        remembered_context[
                            "source"
                        ],

                        remembered_context[
                            "gameId"
                        ]
                    )


                    active_contexts[
                        key
                    ] = remembered_context


            # --------------------------------------
            # MATCH HAT GERADE GEWECHSELT / GEENDET
            # --------------------------------------

            if (
                previous
                and
                current_match_id
                != previous_match_id
            ):

                old_context = previous.get(
                    "context"
                )


                if (
                    old_context
                    and
                    old_context.get(
                        "gameId"
                    )
                ):

                    old_key = (

                        old_context[
                            "source"
                        ],

                        old_context[
                            "gameId"
                        ]
                    )


                    active_contexts[
                        old_key
                    ] = old_context


            previous_slots[
                number
            ] = {

                "matchId":
                    current_match_id,

                "context":
                    (
                        context
                        or
                        last_game_by_slot.get(
                            number
                        )
                    )
            }


        # ==========================================
        # TEAMSTÄNDE REGELMÄSSIG AKTUALISIEREN
        # ==========================================

        now_monotonic = time.monotonic()


        for key, context in (
            active_contexts.items()
        ):

            last_refresh = (
                team_score_last_refresh.get(
                    key,
                    0
                )
            )


            needs_refresh = (

                key
                not in team_score_cache

                or

                (
                    now_monotonic
                    - last_refresh
                    >=
                    TEAM_SCORE_REFRESH_SECONDS
                )
            )


            if needs_refresh:

                old_score = (
                    team_score_cache.get(
                        key
                    )
                )


                new_score = (
                    calculate_team_score(
                        context
                    )
                )


                team_score_cache[
                    key
                ] = new_score


                team_score_last_refresh[
                    key
                ] = now_monotonic


                if (
                    old_score
                    and
                    (
                        old_score.get(
                            "home"
                        )
                        !=
                        new_score.get(
                            "home"
                        )

                        or

                        old_score.get(
                            "away"
                        )
                        !=
                        new_score.get(
                            "away"
                        )
                    )
                ):

                    print(
                        "Mannschaftsstand geändert:",
                        old_score.get(
                            "home"
                        ),
                        ":",
                        old_score.get(
                            "away"
                        ),
                        "→",
                        new_score.get(
                            "home"
                        ),
                        ":",
                        new_score.get(
                            "away"
                        )
                    )


        # ==========================================
        # SCOREBOARDS BAUEN
        # ==========================================

        scoreboards = []


        for slot in slots:

            number = slot[
                "slot"
            ]


            scoreboard = build_scoreboard(

                number,

                slot[
                    "installId"
                ],

                current_documents[
                    number
                ]
            )


            scoreboards.append(
                scoreboard
            )


        # ==========================================
        # JSON
        # ==========================================

        combined = {

            "source":
                "janova-firestore",

            "updated":
                datetime.now()
                .isoformat(
                    timespec="seconds"
                ),

            "pollSeconds":
                POLL_SECONDS,

            "readerCycleMs":
                round((time.monotonic() - started) * 1000),

            "scoreboards":
                scoreboards
        }


        write_json_atomic(
            OUTPUT_COMBINED,
            combined
        )


        for scoreboard in scoreboards:

            filename = (
                f"scoreboard"
                f"{scoreboard['slot']}"
                f".json"
            )


            write_json_atomic(
                filename,
                scoreboard
            )


        # ==========================================
        # STATUS
        # ==========================================

        print_status(
            scoreboards
        )


    except KeyboardInterrupt:

        print()
        print(
            "Live-Reader beendet."
        )

        break


    except Exception as error:

        print()
        print(
            "Fehler im Live-Reader:"
        )

        print(
            repr(error)
        )

        print()
        print(
            "Neuer Versuch in "
            "1 Sekunde ..."
        )


    duration = (
        time.monotonic()
        - started
    )


    sleep_time = max(
        0,
        POLL_SECONDS
        - duration
    )


    time.sleep(
        sleep_time
    )
