#!/bin/env python

import requests
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
    logging.info("Getting datacenters from database")
    query = "SELECT * FROM datacenters;"
    cursor.execute(query)
    rows = cursor.fetchall()
    return {d[0]: d[1] for d in rows}

def get_networks():
    logging.info("Getting networks from database")
    query = "SELECT * FROM networks;"
    cursor.execute(query)
    rows = cursor.fetchall()
    return {(n[0], n[1]): (n[2], n[3]) for n in rows}

def get_routing():
    logging.info("Getting routing information from database")
    query = "SELECT * FROM routing;"
    cursor.execute(query)
    rows = cursor.fetchall()
    return {(r[0], r[1], r[2]): (r[3], r[4]) for r in rows}

def get_datacites():
    logging.info("Getting datacite information from database")
    query = "SELECT * FROM datacite;"
    cursor.execute(query)
    rows = cursor.fetchall()
    return {(d[0], d[1]): (d[2], d[3], d[4]) for d in rows}

def get_stationxml():
    logging.info("Getting stationxml information from database")
    query = "SELECT * FROM stationxml;"
    cursor.execute(query)
    rows = cursor.fetchall()
    return {(s[0], s[1]): (s[2], s[3]) for s in rows}

def test_networks():
    logging.info("Running tests and storing results to database for each available network")
    current_time = datetime.now().replace(microsecond=0)
    with alive_bar(len(networks)) as pbar:
        for net in networks:
            if net not in datacites:
                page_works, has_license = None, None
            else:
                try:
                    r = requests.get(datacites[net][1])
                    page_works = True if r.status_code == 200 else False
                except Exception:
                    page_works = False
                has_license = True if datacites[net][0] is not None else False
            if net not in stationxml:
                xml_doi_match, xml_restriction_match = None, None
            else:
                xml_doi_match = networks[net][1] == stationxml[net][0]
                open = True if stationxml[net][1] in ['open', 'partial'] else False
                xml_restriction_match = has_license == open
            query = "INSERT INTO tests (test_time, code, startdate, doi, page_works, has_license, xml_doi_match, xml_restriction_match) \
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"
            cursor.execute(query , (current_time, net[0], net[1], networks[net][1], page_works, has_license, xml_doi_match, xml_restriction_match))
            cnx.commit()
            pbar()


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
