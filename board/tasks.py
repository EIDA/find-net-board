from celery import shared_task
import requests
import logging
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from datetime import datetime
from django.utils import timezone
import traceback

from .models import Test, Network, Datacenter, Routing, Datacite, Stationxml
from .views import get_FDSN_datacenters, get_EIDA_routing, update_networks_table, update_datacite_table, try_EIDA_routing, try_FDSN_routing, update_stationxml_table, process_networks

logger = logging.getLogger(__name__)

@shared_task
def update_and_run():
    datacenters_datasets, datacenters_urls = get_FDSN_datacenters()
    eida_routing = get_EIDA_routing()
    logger.info("Getting all networks from FDSN and updating database")
    r = requests.get("https://www.fdsn.org/ws/networks/1/query")
    i = 1
    for net in r.json()["networks"]:
        logger.debug(f"Progress {i}/{len(r.json()['networks'])}")
        update_networks_table(net)
        update_datacite_table(net)
        datacenter = try_EIDA_routing(net, eida_routing, datacenters_urls)
        if not datacenter:
            datacenter = try_FDSN_routing(net, datacenters_datasets)
        if datacenter:
            update_stationxml_table(net, datacenters_urls[datacenter])
        i += 1
    logger.info("Finished updating DB from sources")

    logger.info("Running tests and storing results to database for each available network")
    datacenters = {datacenter.name: datacenter.station_url for datacenter in Datacenter.objects.all()}
    networks = {(network.code, network.startdate): (network.enddate, network.doi) for network in Network.objects.all()}
    routing = {(routing.network.code, routing.network.startdate, routing.datacenter): (routing.priority, routing.source) for routing in Routing.objects.all()}
    datacites = {(datacite.network.code, datacite.network.startdate): (datacite.licenses, datacite.page, datacite.publisher) for datacite in Datacite.objects.all()}
    stationxml = {(stationxml.network.code, stationxml.network.startdate): (stationxml.doi, stationxml.restriction) for stationxml in Stationxml.objects.all()}
    current_time = timezone.now().replace(microsecond=0)
    i = 1
    for net in networks:
        logger.debug(f"Progress {i}/{len(networks)}")
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
        network_db = Network.objects.get(code=net[0], startdate=net[1])
        Test(test_time=current_time, network=network_db, doi=networks[net][1], page_works=page_works, has_license=has_license, xml_doi_match=xml_doi_match, xml_restriction_match=xml_restriction_match).save()
        i += 1
    logger.info("Finished running tests for all networks")
