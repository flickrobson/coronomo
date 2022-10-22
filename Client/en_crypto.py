import time
import sqlite3
from struct import pack
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import HKDF

TEK_ROLLING_PERIOD = 144
DATABASE = 'db.sqlite'
METADATA = b"01000000000000000000000000000000"


class ENKeys:
    """
    This class stores and generates keys and values used in the Exposure Notification System. This is an
    implementation of the Apple's cryptography specification provided here:
    https://covid19-static.cdn-apple.com/applications/covid19/current/static/contact-tracing/pdf/ExposureNotification-CryptographySpecificationv1.2.pdf?1
    """

    def __init__(self, metadata=METADATA, tek=None, enin=None, timestamp=None, local_key=True):
        """
        Creates a new ENKeys object

        The only required parameter is ``metadata``. The 4 byte metadata (LSB first) contains the following:
        - Byte 0 - Version
            - Bits 7:6 — Major version (01).
            - Bits 5:4 — Minor version (00).
            - Bits 3:0 — Reserved for future use
        - Byte 1 - Transmit power level.
            - This is the measured radiated transmit power of Bluetooth Advertisement packets, and is used to improve
              distance approximation. The range of this field shall be -127 to +127 dBm.
        - Byte 2 & 3 - Reserved for future use

        If a Temporary Exposure key is given, either the EN Interval Number or Timestamp for that key must also be
        provided. Otherwise, a Temporary Exposure Key is auto-generated based on the current time It will forst check
        the database to see in a key has already been generated for this time.

        local_key indicates whether the generated keys are this devices own keys that will be transmitted to other
        devices. If so, the generated Temporary Exposure Keys will be stored in the local Temporary_Exposure_Keys
        table. This cannot be True if the Temporary Exposure Key is provided.

        :param metadata: metadata as specified in the Exposure Notification Bluetooth Specification
        :param tek:
        :param enin:
        :param timestamp:
        :param local_key:
        """
        self.metadata = metadata

        # If Temporary Exposure Key is not user-defined
        if tek is None or (enin is None and timestamp is None):
            if local_key is None or local_key:
                self.local_key = True
            else:
                self.local_key = False

            self.tek_period = ENKeys.get_tek_period()

            if self.local_key:
                ENKeys.remove_old_db()
                tek_exists = False
                con = sqlite3.connect(DATABASE)
                with con:
                    # Check whether a Temporary Exposure Key has already been generated for this period
                    cur = con.execute("SELECT * "
                                         "FROM Temporary_Exposure_Keys "
                                         "ORDER BY en_interval_number DESC "
                                         "LIMIT 1")

                    res = cur.fetchone()
                    if res:
                        enin = res[1]
                        if enin == self.tek_period:
                            self.tek = res[0]
                            tek_exists = True

                    # Insert the Temporary Exposure Key into the database if it was not in there already
                    if not tek_exists:
                        self.tek = ENKeys.get_tek()
                        con.execute("INSERT INTO Temporary_Exposure_Keys VALUES (?, ?)", (self.tek, self.tek_period))
                        con.commit()

                con.close()

            else:
                self.tek = ENKeys.get_tek()
                self.tek_period = ENKeys.get_tek_period()


        # If the Temporary Exposure Key is user-defined
        else:
            self.local_key = False
            self.tek = tek

            if enin is None:
                self.tek_period = ENKeys.get_tek_period(timestamp)
            else:
                self.tek_period = enin

        self.rpik = self.get_rpik()
        self.aemk = self.get_aemk()
        self.rpi = self.get_rpi()
        self.aem = self.get_aem()

    @staticmethod
    def get_enin(timestamp=None):
        """
        Provides a number for each 10 minute time window that’s shared between all devices participating in the protocol.

        If no timestamp is provided the current timestamp is used.

        :param timestamp: timestamp in Unix Epoch Time
        :return: EN Interval Number
        """
        if timestamp is None:
            timestamp = int(time.time())
        return timestamp // (60 * 10)

    @staticmethod
    def get_enin_timestamp(enin):
        """
        Calculates the timestamp corresponding to the beginning of the EN Interval Number

        :param enin: EN Interval Number
        :return: timestamp in Unix Epoch Time
        """
        return enin * (60 * 10)


    @staticmethod
    def get_tek_period(timestamp=None):
        """
        Calculates the EN Interval Number from when a Temporary Exposure Key is valid. Temporary Exposure Keys roll
        every 144 EN Interval Numbers, so the valid period always starts at a multiple of 144. This is equivalent to
        every 24 hours.

        If no timestamp is provided the current timestamp is used.

        :param timestamp: timestamp in Unix Epoch Time
        :return: most recent EN Interval Number that is a multiple of 144
        """
        enin = ENKeys.get_enin(timestamp)
        return (enin // TEK_ROLLING_PERIOD) * TEK_ROLLING_PERIOD

    @staticmethod
    def get_tek():
        """
        Generate a emporary Exposure Key, whihc is 16 random bytes

        :return: Temporary Exposure Key
        """
        tek = get_random_bytes(16)
        return tek

    def derive_rpi_aem(self):
        """
        Derives the current Rolling Proximity Identifier and Associated Encrypted Metadata.

        :return: Rolling Proximity Identifier, Associated Encrypted Metadata
        """
        self.roll_tek()  # Incase the TEK rolling period has elapsed
        self.rpi = self.get_rpi()
        self.aem = self.get_aem()
        return self.rpi, self.aem

    def roll_tek(self):
        """
        Generates a new TEK if the current time is not within the current TEK's period. Also updates the values of
        RPIK, and AEMK.

        :return: True if the TEK and associated values are changed, False otherwise
        """
        current_period = ENKeys.get_tek_period()
        if self.tek_period != current_period:
            self.tek = self.get_tek()
            self.tek_period = current_period
            self.rpik = self.get_rpik()
            self.aemk = self.get_aemk()

            # Add new Temporary Exposure Key to the database
            if self.local_key:
                ENKeys.remove_old_db()
                con = sqlite3.connect(DATABASE)
                with con:
                    con.execute("INSERT INTO Temporary_Exposure_Keys VALUES (?, ?)", (self.tek, self.tek_period))
                    con.commit()
                con.close()

            return True
        return False

    def get_rpik(self):
        """
        Generates the Rolling Proximity Identifier Key

        The Rolling Proximity Identifier Key is derived from the Temporary Exposure Key and is used in order to
        derive the Rolling Proximity Identifiers

        :return: Rolling Proximity Identifier Key
        """
        rpik = HKDF(master=self.tek, salt=None, context="EN-RPIK".encode("UTF-8"), key_len=16, hashmod=SHA256)
        return rpik

    def get_aemk(self):
        """
        Generates the Associated Encrypted Metadata Key for the current Temporary Exposure Keys.

        The Associated Encrypted Metadata Keys are derived from the Temporary Exposure Keys in order to encrypt
        additional metadata.

        :return: Associated Encrypted Metadata Key
        """
        aemk = HKDF(master=self.tek, salt=None, context="EN-AEMK".encode("UTF-8"), key_len=16, hashmod=SHA256)
        return aemk

    def get_rpi(self, enin=None):
        """
        Generates the Rolling Proximity Identifier for the current Rolling Proximity Identifier Key and EN Interval
        Number.

        Rolling Proximity Identifiers are privacy-preserving identifiers that are broadcast in Bluetooth payloads.
        Each time the Bluetooth Low Energy MAC randomized address changes, we derive a new Rolling Proximity Identifier
        using the Rolling Proximity Identifier Key

        :param enin: the EN Interval Number. If none, the current time's number is used
        :return: Rolling Proximity Identifier
        """
        if enin is None:
            enin = ENKeys.get_enin()
        padded_data = "EN-RPI".encode("UTF-8") + b"\x00" * 6 + pack("<I", enin)
        cipher = AES.new(key=self.rpik, mode=AES.MODE_ECB)
        rpi = cipher.encrypt(padded_data)
        return rpi

    def get_aem(self):
        """
        Encrypts the given ``metadata`` corresponding to the current Rolling Proximity Identifier.

        The Associated Encrypted Metadata is data encrypted along with the Rolling Proximity Identifier, and can only be
        decrypted later if the user broadcasting it tested positive and reveals their Temporary Exposure Key.

        :return: Associated Encrypted Metadata
        """
        cipher = AES.new(key=self.aemk, initial_value=self.rpi, mode=AES.MODE_CTR, nonce=b'')
        aem = cipher.encrypt(self.metadata)
        return aem

    def get_rpi_sequence(self):
        sequence = []
        for enin in range(self.tek_period, self.tek_period + TEK_ROLLING_PERIOD):
            rpi = self.get_rpi(enin)
            sequence.append(rpi)

        return sequence

    @staticmethod
    def remove_old_db():
        enin = ENKeys.get_enin() - (TEK_ROLLING_PERIOD * 14) # 14 days before the current EN Interval Numers

        con = sqlite3.connect(DATABASE)
        with con:
            con.execute("DELETE FROM Temporary_Exposure_Keys WHERE en_interval_number < ?", (enin,))
            con.execute("DELETE FROM Exposures WHERE datetime(timestamp, 'unixepoch') < datetime('now', '-14 days')")
            con.execute("DELETE FROM Diagnosis_Keys WHERE en_interval_number < ?", (enin,))
            con.commit()
        con.close()
