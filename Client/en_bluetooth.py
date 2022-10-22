# How to use en_crypto:
#     - ``from en_crypto import ENKeys``
#     - Create an ENKeys object (at the beginning) which will contain the data you need to broadcast over bluetooth.
#         ``keys = ENKeys(metadata)`` where you provide the metadata based on the EN Bluetooth Specification
#     - Access the keys you need in the advertising payload using ``keys.rpi`` and ``keys.aem``
#     - You must check for when the bluetooth address changes. When it does, update the RPI and AEM using
#         ``keys.derive_rpi_aem``
#     - You shouldn't need to use any other methods from en_crypto

# How to store scanned scanned broadcasts from other devices:
#     - ``import sqlite3``
#     - Look up how to connect to the database and insert values into sqlite databases from python (or see en_crypto.py
#     for examples)
#     - Whenever you scan a EN Bluetooth Broadcast, store the RPI, AEM and the timestamp (in Unix time) in the
#     'Exposures' Table
import traceback

import bluetooth
import sys
from en_crypto import ENKeys
import sqlite3
from datetime import datetime
from datetime import timezone
import time

DATABASE = 'db.sqlite'
keys = ENKeys()


def send():
    """
    Sends Exposure Notification transmission to other devices running the app in range. Transmission includes the RPI
    and AEM.
    """
    keys.derive_rpi_aem()
    print("\nSending")
    uuid = "FD6F"
    service_matches = bluetooth.find_service(uuid=uuid)

    if len(service_matches) == 0:
        print("Couldn't find the Exposure Notification Service")
        return

    print(service_matches)
    for match in service_matches:
        port = match["port"]
        name = match["name"]
        host = match["host"]

        flag = b"\x02\x01\x1A"
        complete_service_uuid = b"\x03\x03\xFD\x6F"
        service_data = b"\x17\x16\xFD\x6F" + keys.rpi + keys.aem
        package = flag + complete_service_uuid + service_data

        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((host, port))
        sock.send(package)
        sock.close()


def receive():
    """
    Receives Exposure Notification transmission from another device. Stores RPI, AEM, and Timestamp in the Exposures
    table of db.sqlite
    """
    while True:
        try:
            server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

            print("\nReceiving")
            port = 1
            server_sock.bind(("", port))
            server_sock.listen(port)

            uuid = "FD6F"
            bluetooth.advertise_service(server_sock, name="Exposure Notification Service", service_id=uuid)

            client_sock, address = server_sock.accept()

            data = client_sock.recv(1024)

            client_sock.close()
            server_sock.close()

            date_time_now = datetime.now()
            timestamp = date_time_now.replace(tzinfo=timezone.utc).timestamp()

            split_rpi = data[11:27]
            split_aem = data[27:]
            print(f"{address} sent rpi {split_rpi}")

            con = sqlite3.connect(DATABASE)
            with con:
                con.execute("INSERT INTO Exposures (rolling_proximity_identifier, associated_encrypted_metadata, "
                            "timestamp) VALUES (?, ?, ?)", (split_rpi, split_aem, timestamp))
                con.commit()
            con.close()

        except Exception:
            print(traceback.format_exc())


def main():
    # In reality these two methods will occur at the same time meaning the device can send and receive the metadata at
    # the same time.
    receive()


if __name__ == "__main__":
    main()
