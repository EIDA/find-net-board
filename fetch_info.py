import requests
import logging
import mysql.connector
from datetime import datetime
import xml.etree.ElementTree as ET
import sys
from alive_progress import alive_bar

logging.basicConfig(level=logging.INFO)

try:
    cnx = mysql.connector.connect(user='root',
                            password='password',
                            host='localhost',
                            database='networks_tests')
except Exception as e:
    logging.error(e)
    logging.error("Database connection problem!")
    sys.exit(1)
cursor = cnx.cursor()

logging.info("Getting all datacenters from FDSN and updating database")
r = requests.get("https://www.fdsn.org/ws/datacenters/1/query?includedatasets=true")
datacenters = {}
for dc in r.json()["datacenters"]:
    station_url = None
    for r in dc["repositories"]:
        if (r["name"] == "archive" or r["name"] == "ARCHIVE") and "datasets" in r:
            datacenters[dc["name"]] = r["datasets"]
            for s in r["services"]:
                if s["name"] == "fdsnws-station-1":
                    station_url = s["url"]
    query = "INSERT INTO datacenters (name, station_url) VALUES (%s, %s) \
    ON DUPLICATE KEY UPDATE station_url = VALUES(station_url);"
    cursor.execute(query, (dc["name"], station_url))
cnx.commit()


logging.info("Getting all networks from FDSN and updating database")
dataciteapi = "https://api.datacite.org/application/vnd.datacite.datacite+json/"
r = requests.get("https://www.fdsn.org/ws/networks/1/query")

with alive_bar(len(r.json()["networks"])) as pbar:
    for net in r.json()["networks"]:
        # networks table
        doi = net["doi"] if net["doi"] else None
        start = datetime.strptime(net["start_date"], "%Y-%m-%d")
        end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else None
        query = "INSERT INTO networks (code, startdate, enddate, doi) VALUES (%s, %s, %s, %s) \
        ON DUPLICATE KEY UPDATE enddate = VALUES(enddate), doi = VALUES(doi);"
        cursor.execute(query, (net["fdsn_code"], start, end, doi))

        # datacite table
        r = requests.get(dataciteapi+net["doi"])
        datacite = r.json()
        licenses = ""
        if datacite.get("rightsList"):
            for l in datacite["rightsList"]:
                licenses += l["rightsUri"] + ", "
        licenses = licenses[:-2] if licenses else None
        query = "INSERT INTO datacite (code, startdate, licenses, page, publisher) VALUES (%s, %s, %s, %s, %s) \
        ON DUPLICATE KEY UPDATE licenses = VALUES(licenses), page = VALUES(page), publisher = VALUES(publisher);"
        cursor.execute(query, (net["fdsn_code"], start, licenses, datacite["url"], datacite["publisher"].get("name")))
        pbar()
