import asyncio
import pickle
import sqlite3
import websockets
import config

DATABASE = 'db.sqlite'
socket_host, socket_port = config.websocket_info()


def positive_otp(otp):
    """
    Sends a One Time Password and the user's temporary exposure keys in the event that they have tested positive. If
    the One Time Password is valid, the keys are added to the server as diagnosis keys.

    :return: Whether the keys were successfully uploaded
    """
    diagnosis_keys = get_data()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = asyncio.get_event_loop().run_until_complete(send_diagnosis_keys(otp, diagnosis_keys))
    return result


async def send_diagnosis_keys(otp, diagnosis_keys):
    """
    Transmits the provided one time password and diagnosis keys to the server

    :return: Whether the keys were successfully uploaded
    """
    uri = "ws://" + socket_host + ":" + socket_port
    async with websockets.connect(uri) as websocket:
        send = pickle.dumps((otp, diagnosis_keys))

        await websocket.send(send)

        incoming = await websocket.recv()
        print(f"< {incoming}")
        if incoming == "Insertion successful":
            return True
        else:
            return False


def get_data():
    """
    Gets the user's temporary exposure keys from the database

    :return: a list of rows where first element is the temporary exposure key and the second is the corresponding EN
    interval number
    """
    con = sqlite3.connect(DATABASE)
    with con:
        cur = con.execute("SELECT * FROM Temporary_Exposure_Keys ")

        diagnosis_keys = cur.fetchall()

    con.close()
    return diagnosis_keys
