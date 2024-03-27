import requests
import logging
from mysql import connector
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)


try:
    cnx = connector.connect(user='root',
                            password='root',
                            host='localhost',
                            database='netstests')
except:
    logging.error('Database connection problem!')
cursor = cnx.cursor()

logging.info("Getting all networks from FDSN")
r = requests.get("https://www.fdsn.org/ws/networks/1/query")

current_time = datetime.now()

for net in r.json()["networks"]:
    # doi test
    doi_result = True if net["doi"] else False
    doi_comment = net["doi"] if net["doi"] else None
    query = "INSERT INTO networks_tests (test_time, name, code, startdate, doi_result, doi_comment) VALUES (%s, %s, %s, %s, %s, %s);"
    cursor.execute(query, (current_time, net["name"], net["fdsn_code"], net["start_date"], doi_result, doi_comment))
    if not net["doi"]:
        continue

    # datacite tests
    dataciteapi = "https://api.datacite.org/application/vnd.datacite.datacite+json/"
    r = requests.get(dataciteapi+net["doi"])
    datacite = r.json()
    # page test
    r.request.get(datacite["url"])
    if r.status_code == 200:
        # success in database
        #query = "UPDATE networks_tests SET doi_result = %s WHERE test_time = %s AND name = %s;"
    else:
        # fail in database
    # open test UNSURE ABOUT THAT
    # license test
    if datacite['rightsList']:
        # success in database
        # store license
    else:
        # fail in database
        # clear comment
    # store publisher in database

    # StationXML test UNSURE HOW TO

    # commit changes for network net
    cnx.commit()

cursor.close()
