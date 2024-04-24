from celery import shared_task
import requests
import logging
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from datetime import datetime
from alive_progress import alive_bar
import traceback

from .models import Test, Network, Datacenter, Routing, Datacite, Stationxml
from .views import get_FDSN_datacenters, get_EIDA_routing, update_networks_table, update_datacite_table, try_EIDA_routing, try_FDSN_routing, update_stationxml_table, process_networks

logger = logging.getLogger(__name__)

@shared_task
def update_from_sources():
    datacenters_datasets, datacenters_urls = get_FDSN_datacenters()
    eida_routing = get_EIDA_routing()
    logging.info("Getting all networks from FDSN and updating database")
    r = requests.get("https://www.fdsn.org/ws/networks/1/query")
    with alive_bar(len(r.json()["networks"])) as pbar:
        for net in r.json()["networks"]:
            update_networks_table(net)
            update_datacite_table(net)
            datacenter = try_EIDA_routing(net, eida_routing, datacenters_urls)
            if not datacenter:
                datacenter = try_FDSN_routing(net, datacenters_datasets)
            if datacenter:
                update_stationxml_table(net, datacenters_urls[datacenter])
            pbar()
