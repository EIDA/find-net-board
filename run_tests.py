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
                            database='netstests')
except Exception as e:
    logging.error(e)
    logging.error("Database connection problem!")
    sys.exit(1)
cursor = cnx.cursor()

logging.info("Getting all networks from FDSN")
r = requests.get("https://www.fdsn.org/ws/networks/1/query")

current_time = datetime.now().replace(microsecond=0)

with alive_bar(len(r.json()["networks"])) as pbar:
    for net in r.json()["networks"]:
        # doi test
        doi = net["doi"] if net["doi"] else None
        query = "INSERT INTO networks_tests (test_time, name, code, startdate, enddate, doi) VALUES (%s, %s, %s, %s, %s, %s);"
        cursor.execute(query, (current_time, net["name"], net["fdsn_code"], net["start_date"], net["end_date"], doi))
        cnx.commit()
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
        license = ""
        if datacite.get("rightsList"):
            for l in datacite["rightsList"]:
                license += l["rightsUri"] + ", "
        license = license[:-2] if license else None
        # store publisher in database
        publisher = datacite["publisher"]["name"] if datacite["publisher"]["name"] else None

        # find datacenter
        r = requests.get("https://www.fdsn.org/ws/datacenters/1/query?includedatasets=true")
        datacenter = None
        datacenter_station_ws = None
        for d in r.json()["datacenters"]:
            for r in d["repositories"]:
                if (r["name"] == "archive" or r["name"] == "ARCHIVE") and "datasets" in r:
                    for dset in r["datasets"]:
                        start = datetime.strptime(net["start_date"], "%Y-%m-%d")
                        end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else datetime.strptime("2100-01-01", "%Y-%m-%d")
                        try:
                            dc_start = datetime.strptime(dset["starttime"], "%Y-%m-%dT%H:%M:%S")
                        except:
                            try:
                                dc_start = datetime.strptime(dset["starttime"], "%Y-%m-%dT%H:%M:%SZ")
                            except:
                                try:
                                    dc_start = datetime.strptime(dset["starttime"], "%Y-%m-%dT%H:%M:%S.%fZ")
                                except:
                                    try:
                                        dc_start = datetime.strptime(dset["starttime"], "%Y-%m-%dT%H:%M:%S.%f")
                                    except:
                                        continue
                        if dset["priority"] == 1 and dset["network"] == net["fdsn_code"] and start <= dc_start <= end:
                            datacenter = d["name"]
                            for s in r["services"]:
                                if s["name"] == "fdsnws-station-1":
                                    datacenter_station_ws = s["url"]
                            break
            if datacenter is not None:
                break

        # stationXML tests
        stationxml_result, stationxml_comment = None, None
        if datacenter is not None:
            r = requests.get(datacenter_station_ws+f'query?network={net["fdsn_code"]}&level=network')
            root = ET.fromstring(r.text)
            namespace = {'ns': 'http://www.fdsn.org/xml/station/1'}
            # doi match
            doi_xml = root.find("./ns:Network/ns:Identifier", namespaces=namespace).text
            # restriction status
            restriction = root.find("./ns:Network", namespaces=namespace).attrib["restrictedStatus"]
            open = True if restriction in ['open', 'partial'] else False
            stationxml_result = True if doi_xml == net["doi"] and (license is not None) == open else False
            stationxml_comment = ""
            if doi_xml != net["doi"]:
                stationxml_comment += "StationXML and FDSN DOIs mismatch, "
            if (license is not None) != open:
                stationxml_comment += "StationXML and FDSN restriction status mismatch, "
            stationxml_comment = stationxml_comment[:-2] if stationxml_comment else None
        else:
            stationxml_comment = "No StationXML found"

        # update database and commit changes for network net
        query = "UPDATE networks_tests SET page_result = %s, license = %s, publisher = %s, datacenter = %s, stationxml_result = %s, stationxml_comment = %s WHERE test_time = %s AND name = %s;"
        cursor.execute(query, (page_result, license, publisher, datacenter, stationxml_result, stationxml_comment, current_time, net["name"]))
        cnx.commit()
        pbar()

cursor.close()
