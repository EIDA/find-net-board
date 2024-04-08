#!/bin/env python

import requests
import logging
import mysql.connector
from datetime import datetime
import xml.etree.ElementTree as ET
import sys
from urllib.parse import urlparse
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

def get_FDSN_datacenters():
    logging.info("Getting all datacenters from FDSN and updating database")
    r = requests.get("https://www.fdsn.org/ws/datacenters/1/query?includedatasets=true")
    datacenters_datasets = {}
    datacenters_urls = {}
    for dc in r.json()["datacenters"]:
        station_url = None
        for r in dc["repositories"]:
            if r["name"] in ["archive", "ARCHIVE", "SEED"] and "datasets" in r:
                datacenters_datasets[dc["name"]] = r["datasets"]
                for s in r["services"]:
                    if s["name"] == "fdsnws-station-1":
                        station_url = s["url"]
        datacenters_urls[dc["name"]] = urlparse(station_url).netloc
        query = "INSERT INTO datacenters (name, station_url) VALUES (%s, %s) \
        ON DUPLICATE KEY UPDATE station_url = VALUES(station_url);"
        cursor.execute(query, (dc["name"], station_url))
    return datacenters_datasets, datacenters_urls

def get_EIDA_routing():
    logging.info("Getting EIDA routing information")
    r = requests.get("https://www.orfeus-eu.org/eidaws/routing/1/query?format=json&service=station")
    return r.json()

def update_networks_table(net):
    doi = net["doi"] if net["doi"] else None
    start = datetime.strptime(net["start_date"], "%Y-%m-%d")
    end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else None
    query = "INSERT INTO networks (code, startdate, enddate, doi) VALUES (%s, %s, %s, %s) \
    ON DUPLICATE KEY UPDATE enddate = VALUES(enddate), doi = VALUES(doi);"
    cursor.execute(query, (net["fdsn_code"], start, end, doi))

def update_datacite_table(net):
    start = datetime.strptime(net["start_date"], "%Y-%m-%d")
    dataciteapi = "https://api.datacite.org/application/vnd.datacite.datacite+json/"
    r = requests.get(dataciteapi+net["doi"])
    datacite = r.json()
    licenses = ""
    if datacite.get("rightsList"):
        for l in datacite["rightsList"]:
            licenses += l["rightsUri"] + ", "
    licenses = licenses[:-2] if licenses else None
    publisher = datacite["publisher"].get("name") if "publisher" in  datacite else None
    query = "INSERT INTO datacite (code, startdate, licenses, page, publisher) VALUES (%s, %s, %s, %s, %s) \
    ON DUPLICATE KEY UPDATE licenses = VALUES(licenses), page = VALUES(page), publisher = VALUES(publisher);"
    cursor.execute(query, (net["fdsn_code"], start, licenses, datacite.get("url"), publisher))

def try_EIDA_routing(net):
    datacenter = None
    start = datetime.strptime(net["start_date"], "%Y-%m-%d")
    end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else datetime.strptime("2100-01-01", "%Y-%m-%d")
    # try EIDA routing to find a match
    for dc in eida_routing:
        for network in dc["params"]:
            try:
                net_start = datetime.strptime(network["start"], "%Y-%m-%dT%H:%M:%S")
            except:
                try:
                    net_start = datetime.strptime(network["start"], "%Y-%m-%dT%H:%M:%SZ")
                except:
                    try:
                        net_start = datetime.strptime(network["start"], "%Y-%m-%dT%H:%M:%S.%f")
                    except:
                        try:
                            net_start = datetime.strptime(network["start"], "%Y-%m-%dT%H:%M:%S.%fZS")
                        except:
                            continue
            if network["net"] == net["fdsn_code"] and start <= net_start <= end:
                datacenter = [d for d, u in datacenters_urls.items() if u == urlparse(dc["url"]).netloc][0]
                break
        if datacenter:
            query = "INSERT INTO routing (code, startdate, datacenter, priority, source) VALUES (%s, %s, %s, %s, %s) \
            ON DUPLICATE KEY UPDATE priority = VALUES(priority), source = VALUES(source);"
            cursor.execute(query, (net["fdsn_code"], start, datacenter, network["priority"], "EIDA"))
            break
    return datacenter

def try_FDSN_routing(net):
    start = datetime.strptime(net["start_date"], "%Y-%m-%d")
    end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else datetime.strptime("2100-01-01", "%Y-%m-%d")
    datacenter = None
    for dc in datacenters_datasets:
        for dset in datacenters_datasets[dc]:
            try:
                dset_start = datetime.strptime(dset["starttime"], "%Y-%m-%dT%H:%M:%S")
            except:
                try:
                    dset_start = datetime.strptime(dset["starttime"], "%Y-%m-%dT%H:%M:%SZ")
                except:
                    try:
                        dset_start = datetime.strptime(dset["starttime"], "%Y-%m-%dT%H:%M:%S.%f")
                    except:
                        try:
                            dset_start = datetime.strptime(dset["starttime"], "%Y-%m-%dT%H:%M:%S.%fZ")
                        except:
                            continue
            if dset["network"] == net["fdsn_code"] and start <= dset_start <= end:
                datacenter = dc
                break
        if datacenter:
            query = "INSERT INTO routing (code, startdate, datacenter, priority, source) VALUES (%s, %s, %s, %s, %s) \
            ON DUPLICATE KEY UPDATE priority = VALUES(priority), source = VALUES(source);"
            cursor.execute(query, (net["fdsn_code"], start, datacenter, dset["priority"], "FDSN"))
            break
    return datacenter

def update_stationxml_table(net, datacenter):
    start = datetime.strptime(net["start_date"], "%Y-%m-%d")
    end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else datetime.strptime("2100-01-01", "%Y-%m-%d")
    url = datacenters_urls[datacenter]
    try:
        r = requests.get("https://"+str(url)+f'/fdsnws/station/1/query?network={net["fdsn_code"]}&level=network')
        root = ET.fromstring(r.text)
    except:
        return
    namespace = {'ns': 'http://www.fdsn.org/xml/station/1'}
    networks = root.findall("./ns:Network", namespaces=namespace)
    doi_xml, restriction = None, None
    for n in networks:
        try:
            xml_start = datetime.strptime(n.attrib["startDate"], "%Y-%m-%dT%H:%M:%S")
        except:
            try:
                xml_start = datetime.strptime(n.attrib["startDate"], "%Y-%m-%dT%H:%M:%SZ")
            except:
                try:
                    xml_start = datetime.strptime(n.attrib["startDate"], "%Y-%m-%dT%H:%M:%S.%f")
                except:
                    try:
                        xml_start = datetime.strptime(n.attrib["startDate"], "%Y-%m-%dT%H:%M:%S.%fZ")
                    except:
                        xml_start = n.attrib["startDate"]
        if start <= xml_start <= end:
            # doi
            doi_xml = n.find("./ns:Identifier", namespaces=namespace)
            doi_xml = doi_xml.text if doi_xml is not None and len(doi_xml.text) < 100 else None
            # restriction status
            restriction = n.attrib.get("restrictedStatus")
    query = "INSERT INTO stationxml (code, startdate, doi, restriction) VALUES (%s, %s, %s, %s) \
    ON DUPLICATE KEY UPDATE doi = VALUES(doi), restriction = VALUES(restriction);"
    cursor.execute(query, (net["fdsn_code"], start, doi_xml, restriction))

def process_networks():
    logging.info("Getting all networks from FDSN and updating database")
    r = requests.get("https://www.fdsn.org/ws/networks/1/query")
    with alive_bar(len(r.json()["networks"])) as pbar:
        for net in r.json()["networks"]:
            update_networks_table(net)
            update_datacite_table(net)
            datacenter = try_EIDA_routing(net)
            if not datacenter:
                datacenter = try_FDSN_routing(net)
            if datacenter:
                update_stationxml_table(net, datacenter)
            cnx.commit()
            pbar()


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    cnx = check_database()
    cursor = cnx.cursor()

    datacenters_datasets, datacenters_urls = get_FDSN_datacenters()
    eida_routing = get_EIDA_routing()
    process_networks()
