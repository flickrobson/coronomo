import string
import secrets
import datetime
import mysql.connector
from mysql.connector import Error
import time


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


def generate_otp(connection):
    cursor = connection.cursor()
    password = ''.join(secrets.choice(string.digits) for i in range(8))
    time_added = datetime.datetime.now()
    try:
        opt_expire = datetime.datetime.now() - datetime.timedelta(minutes=5)
        query = "DELETE FROM coronomo.one_time_password WHERE time_added < %s"
        cursor.execute(query, (opt_expire,))

        cursor = connection.cursor()
        query = "INSERT INTO coronomo.one_time_password (password, time_added) VALUES (%s, %s)"
        cursor.execute(query, (password, time_added))
        connection.commit()
        cursor.close()

        return password

    except Error as err:
        print(f"Error: '{err}'")



def main():
    connection = create_server_connection("172.17.0.2", "root", "sql_password")
    received = input("Press 'g' to generate key ")

    while(received != ""):

        if(received == "g"):
            generate = generate_otp(connection)
            print(generate)
        received = "null"
        received = input("Press 'g' to generate key ")

main()
