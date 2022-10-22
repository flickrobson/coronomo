import asyncio
import sqlite3
import websockets
import pickle
import config
from en_crypto import ENKeys

DATABASE = 'db.sqlite'
socket_host, socket_port = config.websocket_info()


def refresh_diagnosis():
    """
    Initiates a refresh to update the diagnosis keys.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = asyncio.get_event_loop().run_until_complete(get_diagnosis_keys())
    return result


async def get_diagnosis_keys():
    """
    Transmits a request to retrieve the diagnosis keys from the server

    :return: Current Diagnosis Keys
    """
    uri = "ws://" + socket_host + ":" + socket_port
    async with websockets.connect(uri) as websocket:

        send = pickle.dumps("refresh")

        await websocket.send(send)

        incoming = await websocket.recv()
        diagnosis_keys = pickle.loads(incoming)
        print(diagnosis_keys)
        result = check_diagnosis_keys(diagnosis_keys)
    return result


def check_diagnosis_keys(diagnosis_keys):
    """
    Checks if the user has been exposed to any of the diagnosis keys.

    For each diagnosis key, generates a sequence of RPIs from the given TEK and EN Interval Number. It then checks if
    any of the RPIs are contained in the user's 'Exposures' table. If so, the Diagnosis Key is added to the
    'Diagnosis_Keys' table and associations to the contacts are added to the 'Exposures' table.
    Note: this method has not been tested and probably contains bugs
    :param diagnosis_keys: A list of diagnosis keys, where each key is a tuple consisting of the Temporary Exposure
        Key and the EN Interval Number associated with that key.
    :type diagnosis_keys: list[tuple[bytes, int]]
    :return: True if there is a match between at least one of the diagnosis keys and the user's contacts, False
    otherwise.
    """
    match = False
    con = sqlite3.connect(DATABASE)

    for tek, enin in diagnosis_keys:
        key = ENKeys(tek=tek, enin=enin)
        rpis = key.get_rpi_sequence()

        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM Diagnosis_Keys WHERE temporary_exposure_key = ?", (tek,))
            results = cur.fetchall()
            
            if not results:
                query = "SELECT * FROM Exposures WHERE rolling_proximity_identifier IN ({" \
                        "})".format(','.join(['?'] * len(rpis)))
                cur.execute(query, rpis)

                results = cur.fetchall()
                if results:
                    match = True
                    try:
                        cur.execute("INSERT INTO Diagnosis_Keys (temporary_exposure_key, en_interval_number) VALUES (?, ?)",
                                    (tek, enin))
                        diag_key_id = cur.lastrowid
                        contacts = [(diag_key_id, exposure[0]) for exposure in results]
                        cur.executemany("INSERT INTO Close_Contacts VALUES (?, ?)", contacts)
                    except Exception as e:
                        print(e)

            cur.close()

    con.close()
    return match
