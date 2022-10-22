import sqlite3
import threading
from datetime import datetime
from multiprocessing import Process

from flask import Flask, render_template, request
import webview

from en_bluetooth import send, receive
from en_crypto import ENKeys
from en_diagnosis import refresh_diagnosis
from en_positive import positive_otp

DATABASE = 'db.sqlite'
app = Flask(__name__, static_folder='./static', template_folder='./templates')

global sendThread
global receiveThread
global updateThread


@app.route('/')
def index(uploaded=None):
    refresh_diagnosis()
    con = sqlite3.connect(DATABASE)
    exposures = []
    with con:
        cur = con.cursor()
        cur.execute("SELECT id, en_interval_number FROM Diagnosis_keys ORDER BY en_interval_number DESC")

        results = cur.fetchall()
        for result in results:
            timestamp = ENKeys.get_enin_timestamp(result[1])
            date = datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y')

            cur.execute("SELECT COUNT(*) FROM Close_Contacts WHERE diagnosis_key_id = ?", (result[0],))
            num_exposures = cur.fetchone()[0]
            period = ""
            if num_exposures == 1:
                period = "< 15 minutes"
            elif num_exposures <= 4:
                period = "< 1 hour"
            else:
                period = f"{num_exposures // 4} hour{'s' if num_exposures >= 8 else ''}"

            exposures.append((date, period))
        cur.close()
    con.close()

    return render_template('index.html', exposures=exposures, uploaded=uploaded)


@app.route('/positive')
def positive():
    otp = request.args.get('otp')
    result = positive_otp(otp)
    return index(uploaded=result)


class LoopThread(threading.Timer):
    """
    A thread that repeatedly executes on a set period
    """
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def backend():
    """
    Starts backend threads and processes to send and receive bluetooth, and refresh diagnosis keys
    """
    global sendThread
    global receiveThread
    global updateThread
    sendThread = LoopThread(900, send)
    receiveThread = Process(target=receive)
    updateThread = LoopThread(7200, update)

    sendThread.start()
    receiveThread.start()
    updateThread.start()


def update():
    """
    Reloads the window
    """
    window.load_url("/index")


def on_close():
    """
    Executes when the user closes the app. Ensures the backend processes are terminated
    """
    sendThread.cancel()
    receiveThread.terminate()
    updateThread.cancel()


if __name__ == '__main__':
    #app.run()
    backend()
    window = webview.create_window('Coronomo', app, width=400)
    window.closing += on_close
    webview.start()
