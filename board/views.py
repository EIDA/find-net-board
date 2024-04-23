from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Max

from .models import Test, Network, Datacenter, Routing, Datacite, Stationxml

import requests
import logging
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from datetime import datetime
from alive_progress import alive_bar
import traceback

logger = logging.getLogger(__name__)

# main home page view with latest tests
def index(request):
    latest_test_time = Test.objects.aggregate(latest_test_time=Max('test_time'))['latest_test_time']
    tests = Test.objects.filter(test_time=latest_test_time).order_by("-test_time")
    context = {"tests": tests}
    return render(request, "board/index.html", context)


# below view to retrieve tests that match user request
def search_tests(request):
    network_code = request.GET.get('network', None)
    start_date = request.GET.get('start', None)
    end_date = request.GET.get('end', None)

    tests = Test.objects

    if network_code:
        tests = tests.filter(network__code=network_code)

    if start_date:
        tests = tests.filter(test_time__gte=start_date)

    if end_date:
        tests = tests.filter(test_time__lte=end_date)

    tests_data = [{
        'test_time': test.test_time,
        'network_code': test.network.code,
        'start_date': test.network.startdate,
        'doi': test.doi,
        'page_works': test.page_works,
        'has_license': test.has_license,
        'xml_doi_match': test.xml_doi_match,
        'xml_restriction_match': test.xml_restriction_match
    } for test in tests]

    return JsonResponse({'tests': tests_data})


# function to tell if user is admin
def is_admin(user):
    return user.is_authenticated and user.is_staff


# below view can only be used by admin to run tests on will
@user_passes_test(is_admin)
def run_tests(request):
    logger.info("Running tests and storing results to database for each available network")
    try:
        datacenters = {datacenter.name: datacenter.station_url for datacenter in Datacenter.objects.all()}
        networks = {(network.code, network.startdate): (network.enddate, network.doi) for network in Network.objects.all()}
        routing = {(routing.network.code, routing.network.startdate, routing.datacenter): (routing.priority, routing.source) for routing in Routing.objects.all()}
        datacites = {(datacite.network.code, datacite.network.startdate): (datacite.licenses, datacite.page, datacite.publisher) for datacite in Datacite.objects.all()}
        stationxml = {(stationxml.network.code, stationxml.network.startdate): (stationxml.doi, stationxml.restriction) for stationxml in Stationxml.objects.all()}
        current_time = timezone.now().replace(microsecond=0)
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
                network_db = Network.objects.get(code=net[0], startdate=net[1])
                Test(test_time=current_time, network=network_db, doi=networks[net][1], page_works=page_works, has_license=has_license, xml_doi_match=xml_doi_match, xml_restriction_match=xml_restriction_match).save()
                pbar()
    except Exception as e:
        traceback.print_exc()
        logger.error(e)
        return HttpResponse(str(e), status=500)
    return HttpResponse(status=200)


# below view can only be used by admin to update database on will
@user_passes_test(is_admin)
def update_db_from_sources(request):
    try:
        datacenters_datasets, datacenters_urls = get_FDSN_datacenters()
        eida_routing = get_EIDA_routing()
        process_networks(datacenters_datasets, datacenters_urls, eida_routing)
    except Exception as e:
        traceback.print_exc()
        logger.error(e)
        return HttpResponse(str(e), status=500)
    return HttpResponse(status=200)

def get_FDSN_datacenters():
    logger.info("Getting all datacenters from FDSN and updating database")
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
        datacenters_urls[dc["name"]] = urlparse(station_url).netloc if station_url is not None else ''
        Datacenter(name=dc["name"], station_url=station_url).save()
    return datacenters_datasets, datacenters_urls

def get_EIDA_routing():
    logging.info("Getting EIDA routing information")
    r = requests.get("https://www.orfeus-eu.org/eidaws/routing/1/query?format=json&service=station")
    return r.json()

def update_networks_table(net):
    doi = net["doi"] if net["doi"] else None
    start = datetime.strptime(net["start_date"], "%Y-%m-%d")
    end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else None
    Network.objects.update_or_create(code=net["fdsn_code"], startdate=start, defaults={"enddate": end, "doi": doi})

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
    network_db = Network.objects.get(code=net["fdsn_code"], startdate=start)
    Datacite.objects.update_or_create(network=network_db, defaults={"licenses": licenses, "page": datacite.get("url"), "publisher": publisher})

def try_EIDA_routing(net, eida_routing, datacenters_urls):
    datacenter = None
    start = datetime.strptime(net["start_date"], "%Y-%m-%d")
    end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else datetime.strptime("2100-01-01", "%Y-%m-%d")
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
            network_db = Network.objects.get(code=net["fdsn_code"], startdate=start)
            datacenter_db = Datacenter.objects.get(pk=datacenter)
            Routing.objects.update_or_create(network=network_db, datacenter=datacenter_db, defaults={"priority": network["priority"], "source": "EIDA"})
            break
    return datacenter

def try_FDSN_routing(net, datacenters_datasets):
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
            network_db = Network.objects.get(code=net["fdsn_code"], startdate=start)
            datacenter_db = Datacenter.objects.get(pk=datacenter)
            Routing.objects.update_or_create(network=network_db, datacenter=datacenter_db, defaults={"priority": dset["priority"], "source": "FDSN"})
            break
    return datacenter

def update_stationxml_table(net, url):
    start = datetime.strptime(net["start_date"], "%Y-%m-%d")
    end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else datetime.strptime("2100-01-01", "%Y-%m-%d")
    try:
        r = requests.get("https://"+url+f'/fdsnws/station/1/query?network={net["fdsn_code"]}&level=network')
        root = ET.fromstring(r.text)
    except Exception:
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
    network_db = Network.objects.get(code=net["fdsn_code"], startdate=start)
    Stationxml.objects.update_or_create(network=network_db, defaults={"doi": doi_xml, "restriction": restriction})

def process_networks(datacenters_datasets, datacenters_urls, eida_routing):
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
