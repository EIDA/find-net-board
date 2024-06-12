from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Max, Count, Case, When, FloatField, F, Q, ExpressionWrapper

from .models import Fdsn_registry, Consistency, Eida_routing, Datacenter, Datacite, Stationxml

import requests
import logging
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from datetime import datetime
from alive_progress import alive_bar
import traceback
import re

logger = logging.getLogger(__name__)

# main home page view with latest tests
def index(request):
    latest_test_time = Consistency.objects.aggregate(latest_test_time=Max('test_time'))['latest_test_time']
    tests = Consistency.objects.filter(test_time=latest_test_time)
    for test in tests:
        if test.fdsn_net is not None and re.match(r'^[0-9XYZ]', test.fdsn_net.netcode):
            test.fdsn_net.netcode = f"{test.fdsn_net.netcode}{test.fdsn_net.startdate.year}"
        elif test.xml_net is not None and re.match(r'^[0-9XYZ]', test.xml_net.netcode):
            test.xml_net.netcode = f"{test.xml_net.netcode}{test.xml_net.startdate.year}"
        elif test.eidarout_net is not None and re.match(r'^[0-9XYZ]', test.eidarout_net.netcode):
            test.eidarout_net.netcode = f"{test.eidarout_net.netcode}{test.eidarout_net.startdate.year}"
    context = {'tests': tests}
    return render(request, "board/index.html", context)


# below view to retrieve tests that match user request
def search_tests(request):
    network_code = request.GET.get('network', None)
    start_date = request.GET.get('start', None)
    end_date = request.GET.get('end', None)

    tests = Consistency.objects.order_by('-test_time').all()

    if network_code:
        tests = tests.filter(fdsn_net__netcode=network_code)

    if start_date:
        tests = tests.filter(test_time__gte=start_date)

    if end_date:
        tests = tests.filter(test_time__lte=end_date)

    tests_data = []
    for test in tests:
        if test.fdsn_net is not None and re.match(r'^[0-9XYZ]', test.fdsn_net.netcode):
            netcode = f"{test.fdsn_net.netcode}{test.fdsn_net.startdate.year}"
        elif test.xml_net is not None and re.match(r'^[0-9XYZ]', test.xml_net.netcode):
            netcode = f"{test.xml_net.netcode}{test.xml_net.startdate.year}"
        elif test.eidarout_net is not None and re.match(r'^[0-9XYZ]', test.eidarout_net.netcode):
            netcode = f"{test.eidarout_net.netcode}{test.eidarout_net.startdate.year}"
        else:
            netcode = test.fdsn_net.netcode if test.fdsn_net is not None else (test.xml_net.netcode if test.xml_net is not None else test.eidarout_net.netcode)
        tests_data.append({
            'test_time': test.test_time,
            'datacenter': test.xml_net.datacenter.name if test.xml_net is not None else (test.eidarout_net.datacenter.name if test.eidarout_net is not None else '-'),
            'network_code': netcode,
            'start_date': test.fdsn_net.startdate if test.fdsn_net is not None else (test.xml_net.startdate if test.xml_net is not None else test.eidarout_net.startdate),
            'doi': test.doi,
            'fdsn_net': True if test.fdsn_net is not None else False,
            'xml_net': True if test.xml_net is not None else False,
            'eidarout_net': True if test.eidarout_net is not None else False,
            'page_works': test.page_works,
            'has_license': test.has_license,
            'xml_doi_match': test.xml_doi_match
        })

    return JsonResponse({'tests': tests_data})


# below view to show available test runs
def test_runs(request):
    unique_test_times = Consistency.objects.values('test_time').annotate(
        count=Count('test_time'),
        true_page_count=Count(Case(When(page_works=True, then=1))),
        true_license_count=Count(Case(When(has_license=True, then=1))),
        true_xml_doi_match_count=Count(Case(When(xml_doi_match=True, then=1))),
        null_fdsn_net_count=Count(Case(When(fdsn_net__isnull=False, then=1))),
        null_xml_net_count=Count(Case(When(xml_net__isnull=False, then=1))),
        null_eidarout_net_count=Count(Case(When(eidarout_net__isnull=False, then=1)))
    ).annotate(
        true_page_percentage=ExpressionWrapper((F('true_page_count') * 100.0) / F('count'), output_field=FloatField()),
        true_license_percentage=ExpressionWrapper((F('true_license_count') * 100.0) / F('count'), output_field=FloatField()),
        true_xml_doi_match_percentage=ExpressionWrapper((F('true_xml_doi_match_count') * 100.0) / F('count'), output_field=FloatField()),
        null_fdsn_net_percentage=ExpressionWrapper((F('null_fdsn_net_count') * 100.0) / F('count'), output_field=FloatField()),
        null_xml_net_percentage=ExpressionWrapper((F('null_xml_net_count') * 100.0) / F('count'), output_field=FloatField()),
        null_eidarout_net_percentage=ExpressionWrapper((F('null_eidarout_net_count') * 100.0) / F('count'), output_field=FloatField())
    ).order_by('-test_time')

    return render(request, "board/test_runs.html", {'unique_test_times': list(unique_test_times)})


# below view to show tests of specific datacenter
def datacenter_tests(request, datacenter_name):
    try:
        datacenter = Datacenter.objects.get(name=datacenter_name)
    except Datacenter.DoesNotExist:
        return HttpResponse("<h1>Not Found</h1>Datacenter does not exist!", status=404)
    start_date = request.GET.get('start', None)
    end_date = request.GET.get('end', None)

    consistencies = Consistency.objects.filter(Q(xml_net__datacenter__name=datacenter_name) | Q(eidarout_net__datacenter__name=datacenter_name))

    if not start_date and not end_date:
        latest_test_time = Consistency.objects.aggregate(latest_test_time=Max('test_time'))['latest_test_time']
        consistencies = consistencies.filter(test_time=latest_test_time)
    else:
        if start_date:
            consistencies = consistencies.filter(test_time__gte=start_date)
        if end_date:
            consistencies = consistencies.filter(test_time__lte=end_date)


    consistency_data = []
    for consistency in consistencies:
        if consistency.xml_net is not None and re.match(r'^[0-9XYZ]', consistency.xml_net.netcode):
            netcode = f"{consistency.xml_net.netcode}{consistency.xml_net.startdate.year}"
        elif consistency.eidarout_net is not None and re.match(r'^[0-9XYZ]', consistency.eidarout_net.netcode):
            netcode = f"{consistency.eidarout_net.netcode}{consistency.eidarout_net.startdate.year}"
        else:
            netcode = consistency.xml_net.netcode if consistency.xml_net is not None else consistency.eidarout_net.netcode
        consistency_data.append({
            'test_time': consistency.test_time,
            'network_code': netcode,
            'start_date': consistency.xml_net.startdate if consistency.xml_net is not None else consistency.eidarout_net.startdate,
            'doi': consistency.doi,
            'fdsn_net': True if consistency.fdsn_net is not None else False,
            'xml_net': True if consistency.xml_net is not None else False,
            'eidarout_net': True if consistency.eidarout_net is not None else False,
            'page_works': consistency.page_works,
            'has_license': consistency.has_license,
            'xml_doi_match': consistency.xml_doi_match
        })

    context = {'datacenter_name': datacenter_name.upper(), 'tests': consistency_data}
    return render(request, "board/datacenter_tests.html", context)


# function to tell if user is admin
def is_admin(user):
    return user.is_authenticated and user.is_staff


# below view can only be used by admin to run tests on will
@user_passes_test(is_admin)
def run_tests(request):
    try:
        current_time = timezone.now().replace(microsecond=0)
        # starting from Fdsn_registry table
        logger.info("Making consistency checks starting from FDSN registry")
        with alive_bar(len(Fdsn_registry.objects.all())) as pbar:
            for net in Fdsn_registry.objects.all():
                fdsn_end = net.enddate if net.enddate is not None else datetime.strptime("2100-01-01", "%Y-%m-%d").date()
                routings = Eida_routing.objects.filter(netcode=net.netcode, startdate__range=(net.startdate, fdsn_end))
                datacite = Datacite.objects.filter(network=net).first()
                if datacite is None:
                    page_works, has_license = None, None
                else:
                    try:
                        r = requests.get(datacite.page, timeout=10)
                        page_works = True if r.status_code == 200 else False
                    except Exception:
                        page_works = False
                    has_license = True if datacite.licenses is not None else False
                if not routings.exists():
                    xmls = Stationxml.objects.filter(netcode=net.netcode, startdate__range=(net.startdate, fdsn_end))
                    if xmls.exists():
                        for xml in xmls:
                            if net.doi is None:
                                doi_match = None
                            elif xml.doi is None:
                                doi_match = False
                            else:
                                doi_match = net.doi.lower()==xml.doi.lower()
                            Consistency(test_time=current_time, fdsn_net=net, xml_net=xml, doi=net.doi, page_works=page_works, has_license=has_license, xml_doi_match=doi_match).save()
                    else:
                        Consistency(test_time=current_time, fdsn_net=net, doi=net.doi, page_works=page_works, has_license=has_license).save()
                else:
                    for rout in routings:
                        rout_end = rout.enddate if rout.enddate is not None else datetime.strptime("2100-01-01", "%Y-%m-%d").date()
                        start_search = min(rout.startdate, net.startdate)
                        end_search = max(rout_end, fdsn_end)
                        xml = Stationxml.objects.filter(datacenter=rout.datacenter.name, netcode=rout.netcode, startdate__range=(start_search, end_search)).first()
                        if net.doi is None or xml is None:
                            doi_match = None
                        elif xml.doi is None:
                            doi_match = False
                        else:
                            doi_match = net.doi.lower()==xml.doi.lower()
                        Consistency(test_time=current_time, fdsn_net=net, eidarout_net=rout, xml_net=xml if xml is not None else None, doi=net.doi, page_works=page_works, has_license=has_license, xml_doi_match=doi_match).save()
                pbar()
        # starting from Stationxml table
        logger.info("Making consistency checks starting from StationXML files")
        unlinked_stationxml = Stationxml.objects.filter(
            ~Q(id__in=Consistency.objects.filter(test_time=current_time).exclude(xml_net_id__isnull=True).values_list('xml_net_id', flat=True))
        )
        with alive_bar(len(unlinked_stationxml)) as pbar:
            for net in unlinked_stationxml:
                routings = Eida_routing.objects.filter(Q(netcode=net.netcode, startdate__lte=net.startdate, enddate__gte=net.startdate)
                    | Q(netcode=net.netcode, startdate__lte=net.startdate, enddate__isnull=True))
                if not routings.exists():
                    Consistency(test_time=current_time, xml_net=net, doi=net.doi).save()
                for rout in routings:
                    Consistency(test_time=current_time, xml_net=net, eidarout_net=rout, doi=net.doi).save()
                pbar()
        # starting from Eida_routing table
        logger.info("Making consistency checks starting from EIDA routing registry")
        unlinked_routing = Eida_routing.objects.filter(
            ~Q(id__in=Consistency.objects.filter(test_time=current_time).exclude(eidarout_net_id__isnull=True).values_list('eidarout_net_id', flat=True))
        )
        with alive_bar(len(unlinked_routing)) as pbar:
            for net in unlinked_routing:
                Consistency(test_time=current_time, eidarout_net=net).save()
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
        get_FDSN_networks()
        get_FDSN_datacenters()
        get_EIDA_routing()
    except Exception as e:
        traceback.print_exc()
        logger.error(e)
        return HttpResponse(str(e), status=500)
    return HttpResponse(status=200)

def get_FDSN_networks():
    logger.info("Getting all networks from FDSN and updating database")
    r = requests.get("https://www.fdsn.org/ws/networks/1/query")
    with alive_bar(len(r.json()["networks"])) as pbar:
        for net in r.json()["networks"]:
            doi = net["doi"] if net["doi"] else None
            start = datetime.strptime(net["start_date"], "%Y-%m-%d")
            end = datetime.strptime(net["end_date"], "%Y-%m-%d") if net["end_date"] else None
            obj, created = Fdsn_registry.objects.update_or_create(netcode=net["fdsn_code"], startdate=start, defaults={"enddate": end, "doi": doi})
            if net["doi"] != "":
                update_datacite_table(obj)
            pbar()

def update_datacite_table(net):
    dataciteapi = "https://api.datacite.org/application/vnd.datacite.datacite+json/"
    r = requests.get(dataciteapi+net.doi)
    datacite = r.json()
    licenses = datacite.get("rightsList") if datacite.get("rightsList") != [] else None
    publisher = datacite["publisher"].get("name") if "publisher" in  datacite else None
    dateavail = None
    for d in datacite.get("dates", []):
        if d["dateType"] == "Available":
            if len(d["date"]) == 4:
                dateavail = d["date"] + "-01-01"
            else:
                dateavail = d["date"].split('/')[0]
    Datacite.objects.update_or_create(network=net, defaults={"licenses": licenses, "page": datacite.get("url"), "publisher": publisher, "date_available": dateavail})

def get_FDSN_datacenters():
    logger.info("Getting all datacenters from FDSN and updating database")
    r = requests.get("https://www.fdsn.org/ws/datacenters/1/query")
    with alive_bar(len(r.json()["datacenters"])) as pbar:
        for dc in r.json()["datacenters"]:
            station_url = None
            for r in dc["repositories"]:
                for s in r["services"]:
                    if s["name"] == "fdsnws-station-1":
                        station_url = s["url"]
            datacenter = Datacenter(name=dc["name"], station_url=urlparse(station_url).netloc if station_url is not None else None)
            datacenter.save()
            if dc["name"] in ["GEOFON", "ODC", "ETH", "RESIF", "INGV", "LMU", "ICGC", "NOA", "BGR", "NIEP", "KOERI", "UIB-NORSAR"]:
                update_stationxml_table(datacenter)
            pbar()

def update_stationxml_table(datacenter):
    try:
        r = requests.get(f"https://{datacenter.station_url}/fdsnws/station/1/query?level=network")
        root = ET.fromstring(r.text)
    except Exception:
        return
    namespace = {'ns': 'http://www.fdsn.org/xml/station/1'}
    networks = root.findall("./ns:Network", namespaces=namespace)
    for n in networks:
        try:
            net_start = datetime.strptime(n.attrib["startDate"], "%Y-%m-%dT%H:%M:%S").date()
        except:
            try:
                net_start = datetime.strptime(n.attrib["startDate"], "%Y-%m-%dT%H:%M:%SZ").date()
            except:
                try:
                    net_start = datetime.strptime(n.attrib["startDate"], "%Y-%m-%dT%H:%M:%S.%f").date()
                except:
                    try:
                        net_start = datetime.strptime(n.attrib["startDate"], "%Y-%m-%dT%H:%M:%S.%fZS").date()
                    except:
                        net_start = n.attrib["startDate"][:10]
        try:
            net_end = datetime.strptime(n.attrib.get("endDate"), "%Y-%m-%dT%H:%M:%S").date()
        except:
            try:
                net_end = datetime.strptime(n.attrib.get("endDate"), "%Y-%m-%dT%H:%M:%SZ").date()
            except:
                try:
                    net_end = datetime.strptime(n.attrib.get("endDate"), "%Y-%m-%dT%H:%M:%S.%f").date()
                except:
                    try:
                        net_end = datetime.strptime(n.attrib.get("endDate"), "%Y-%m-%dT%H:%M:%S.%fZS").date()
                    except:
                        try:
                            net_end = n.attrib.get("endDate")[:10]
                        except:
                            net_end = None
        doi = n.find("./ns:Identifier", namespaces=namespace)
        doi = doi.text if doi is not None and len(doi.text) < 100 else None
        Stationxml.objects.update_or_create(datacenter=datacenter, netcode=n.attrib["code"], startdate=net_start, defaults={"enddate": net_end, "doi": doi, "restriction": n.attrib.get("restrictedStatus")})

def get_EIDA_routing():
    logger.info("Getting EIDA routing information")
    r = requests.get("https://www.orfeus-eu.org/eidaws/routing/1/query?format=json&service=station")
    with alive_bar(len(r.json())) as pbar:
        for dc in r.json():
            # get datacenter from database
            try:
                datacenter = Datacenter.objects.get(station_url=urlparse(dc["url"]).netloc)
            except:
                print(dc["url"])
            for net in dc["params"]:
                try:
                    net_start = datetime.strptime(net["start"], "%Y-%m-%dT%H:%M:%S").date()
                except:
                    net_start = datetime.strptime(net["start"], "%Y-%m-%dT%H:%M:%S.%f").date()
                try:
                    net_end = datetime.strptime(net["end"], "%Y-%m-%dT%H:%M:%S").date()
                except:
                    try:
                        net_end = datetime.strptime(net["end"], "%Y-%m-%dT%H:%M:%S.%f").date()
                    except:
                        net_end = None
                Eida_routing.objects.update_or_create(netcode=net["net"], datacenter=datacenter, startdate=net_start, defaults={"enddate": net_end, "priority": net["priority"]})
            pbar()
