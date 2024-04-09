#!/bin/env python

import logging
import mysql.connector
from datetime import datetime
import sys
from alive_progress import alive_bar


def check_database():
    try:
        cnx = mysql.connector.connect(user='root',
                                password='password',
                                host='localhost',
                                database='networks_tests')
    except Exception as e:
        logging.error(e)
        logging.error("Database connection problem!")
        sys.exit(1)
    return cnx

def get_datacenters():
    query = "SELECT * FROM datacenters;"
    cursor.execute(query)
    rows = cursor.fetchall()
    return {d[0]: d[1] for d in rows}

def get_networks():
    query = "SELECT * FROM networks;"
    cursor.execute(query)
    rows = cursor.fetchall()
    return {(n[0], n[1]): (n[2], n[3]) for n in rows}

def get_routing():
    query = "SELECT * FROM networks;"
    cursor.execute(query)
    rows = cursor.fetchall()
    return {(r[0], r[1], r[2]): (r[3], r[4]) for r in rows}

def get_datacites():
    query = "SELECT * FROM networks;"
    cursor.execute(query)
    rows = cursor.fetchall()
    return {(d[0], d[1]): (d[2], d[3], d[4]) for d in rows}

def get_stationxml():
    query = "SELECT * FROM networks;"
    cursor.execute(query)
    rows = cursor.fetchall()
    return {(s[0], s[1]): (s[2], s[3]) for s in rows}

def test_networks():
    current_time = datetime.now().replace(microsecond=0)
    for net in networks:
        pass


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    cnx = check_database()
    cursor = cnx.cursor()

    datacenters = get_datacenters()
    networks = get_networks()
    routing = get_routing()
    datacites = get_datacites()
    stationxml = get_stationxml()

    test_networks()

    cursor.close()
    cnx.close()
