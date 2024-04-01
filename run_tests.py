import requests
import logging
import mysql.connector
from datetime import datetime
import xml.etree.ElementTree as ET
import sys

logging.basicConfig(level=logging.DEBUG)


try:
    cnx = mysql.connector.connect(user='root',
                            password='password',
                            host='localhost',
                            database='netstests')
except Exception as e:
    logging.error(e)
    logging.error('Database connection problem!')
    sys.exit(1)
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
    r = requests.get(datacite["url"])
    page_result = True if r.status_code == 200 else False
    # license test
    license_result = True if datacite["rightsList"] else False
    license_comment = ""
    if license_result:
        for license in datacite["rightsList"]:
            license_comment += license["rightsUri"] + ", "
    license_comment = license_comment[:-2] if license_comment else None
    # store publisher in database
    publisher = datacite["publisher"]["name"] if datacite["publisher"]["name"] else None

    # find datacenter
    r = requests.get("https://www.fdsn.org/ws/datacenters/1/query?includedatasets=true")
    datacenter = None
    datacenter_station_ws = None
    for d in r.json()["datacenters"]:
        for r in d["repositories"]:
            if r["name"] == "archive" or r["name"] == "ARCHIVE":
                for dset in r["datasets"]:
                    start = datetime.strptime(net["start_date"], "%Y-%m-%d")
                    end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else datetime.strptime("2100-01-01", "%Y-%m-%d")
                    try:
                        dc_start = datetime.strptime(dset["starttime"], "%Y-%m-%dT%H:%M:%S.%fZ")
                    except:
                        print(dset["starttime"])
                    if dset["priority"] == 1 and dset["network"] == net["fdsn_code"] and start <= dc_start <= end:
                        datacenter = d["name"]
                        for s in r["services"]:
                            if s["name"] == "fdsnws-station-1":
                                datacenter_station_ws = s["url"]
                        break
        if datacenter is not None:
            break

    # stationXML tests
    r = requests.get(datacenter_station_ws+f'query?network={net["fdsn_code"]}&level=network')
    root = ET.fromstring(r.text)
    namespace = {'ns': 'http://www.fdsn.org/xml/station/1'}
    # doi match
    doi = root.find("./ns:Network/ns:Identifier", namespaces=namespace).text
    # restriction status
    restriction = root.find("./ns:Network", namespaces=namespace).attrib["restrictedStatus"]
    open = True if restriction in ['open', 'partial'] else False
    stationxml_result = True if doi == net["doi"] and license_result == open else False
    stationxml_comment = ""
    if doi != net["doi"]:
        stationxml_comment += "StationXML and FDSN DOIs mismatch, "
    if license_result != open:
        stationxml_comment += "StationXML and FDSN restriction status mismatch, "
    stationxml_comment = stationxml_comment[:-2] if stationxml_comment else None

    # update database and commit changes for network net
    query = "UPDATE networks_tests SET page_result = %s, license_result = %s, license_comment = %s, publisher = %s, datacenter = %s, stationxml_result = %s, stationxml_comment = %s WHERE test_time = %s AND name = %s;"
    cursor.execute(query, (page_result, license_result, license_comment, publisher, datacenter, stationxml_result, stationxml_comment, current_time, net["name"]))
    cnx.commit()

cursor.close()
