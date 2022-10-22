import asyncio
import websockets
import datetime
import mysql.connector
from mysql.connector import Error
import pickle
import config

mysql_host, mysql_user, mysql_password = config.database_info()
socket_host, socket_port = config.websocket_info()


def create_server_connection(host_name, user_name, user_password):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password
        )
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")

    return connection


def get_diagnosis_keys(connection):
    cursor = connection.cursor()

    diagnosis_keys = []

    try:
        query = "SELECT temp_exposure_key, en_interval_num FROM coronomo.diagnosis_keys"


        cursor.execute(query)

        for (temp_exposure_key, en_interval_num) in cursor:
            diagnosis_keys.append((temp_exposure_key, en_interval_num))

        print("Selection successful")

    except Error as err:
        print(f"Error: '{err}'")

    return diagnosis_keys


def check_otp(connection, otp):
    cursor = connection.cursor(buffered=True)


    try:
        opt_expire = datetime.datetime.now() - datetime.timedelta(minutes=15)
        query = "DELETE FROM coronomo.one_time_password WHERE time_added < %s"
        cursor.execute(query, (opt_expire,))
        cursor.close()

        cursor = connection.cursor(buffered=True)
        query = "SELECT * FROM coronomo.one_time_password WHERE password = %s"
        cursor.execute(query, (otp,))

        print(cursor.fetchall())

        if cursor.rowcount > 0:
            query = "DELETE FROM coronomo.one_time_password WHERE password = %s"
            cursor.execute(query, (otp,))
            connection.commit()
            return True

        else:
            connection.commit()        
            return False
            

    except Error as err:
        print(f"Error: '{err}'")


def insert_diagnosis_keys(connection, diagnosis_keys):
    cursor = connection.cursor()

    try:
        
        for i in diagnosis_keys:
            print(i)

            query = "INSERT INTO coronomo.diagnosis_keys(temp_exposure_key, en_interval_num) VALUES (_binary %s, %s)"
            cursor.execute(query, i)

        connection.commit()

        return True

    except Error as err:
        print(f"Error: '{err}'")


def main():
    connection = create_server_connection(mysql_host, mysql_user, mysql_password)

    async def server(websocket, path):
    
        incoming = await websocket.recv()

        load = pickle.loads(incoming)

        if(load == "refresh"):
            send_back = pickle.dumps(get_diagnosis_keys(connection))
        else:
            otp,diagnosis_keys = load
        
            insert_successful = False

            print(otp)
            print(diagnosis_keys)

            if(check_otp(connection, otp)):
                print("Valid")
                insert_successful = insert_diagnosis_keys(connection, diagnosis_keys)
            
            if(insert_successful):
                send_back = "Insertion successful"
            else:
                send_back = "Insertion not successful"

        
        await websocket.send(send_back)



    start_server = websockets.serve(server, port=socket_port)
    print("Server started")

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

main()


