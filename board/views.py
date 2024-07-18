import logging
import re
import traceback
import xml.etree.ElementTree as ET
import datetime
from urllib.parse import urlparse

import requests
from tqdm import tqdm
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Max, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import (
    Consistency,
    Datacenter,
    Datacite,
    Eida_routing,
    Fdsn_registry,
    Stationxml,
)

logger = logging.getLogger(__name__)


# main home page view with latest tests
def index(request):
    latest_test_time = Consistency.objects.aggregate(latest_test_time=Max("test_time"))[
        "latest_test_time"
    ]
    tests = Consistency.objects.filter(test_time=latest_test_time)
    for test in tests:
        if test.fdsn_net is not None and re.match(r"^[0-9XYZ]", test.fdsn_net.netcode):
            test.fdsn_net.netcode = (
                f"{test.fdsn_net.netcode}{test.fdsn_net.startdate.year}"
            )
        elif test.xml_net is not None and re.match(r"^[0-9XYZ]", test.xml_net.netcode):
            test.xml_net.netcode = (
                f"{test.xml_net.netcode}{test.xml_net.startdate.year}"
            )
        elif test.eidarout_net is not None and re.match(
            r"^[0-9XYZ]", test.eidarout_net.netcode
        ):
            test.eidarout_net.netcode = (
                f"{test.eidarout_net.netcode}{test.eidarout_net.startdate.year}"
            )
    context = {"tests": tests}
    return render(request, "board/index.html", context)


# below view to retrieve tests that match user request
def search_tests(request):
    network_code = request.GET.get("network", None)
    start_date = request.GET.get("start", None)
    end_date = request.GET.get("end", None)
    datacenters = request.GET.get("datacenters", "all")

    tests = Consistency.objects.order_by("-test_time").all()

    if network_code:
        tests = tests.filter(fdsn_net__netcode=network_code)

    if start_date:
        tests = tests.filter(test_time__gte=start_date)

    if end_date:
        tests = tests.filter(test_time__lte=end_date)

    if datacenters == "eida":
        tests = tests.filter(Q(xml_net__isnull=False) | Q(eidarout_net__isnull=False))
    elif datacenters == "non-eida":
        tests = tests.filter(Q(xml_net__isnull=True) & Q(eidarout_net__isnull=True))

    tests_data = []
    for test in tests:
        if test.fdsn_net is not None and re.match(r"^[0-9XYZ]", test.fdsn_net.netcode):
            netcode = f"{test.fdsn_net.netcode}{test.fdsn_net.startdate.year}"
        elif test.xml_net is not None and re.match(r"^[0-9XYZ]", test.xml_net.netcode):
            netcode = f"{test.xml_net.netcode}{test.xml_net.startdate.year}"
        elif test.eidarout_net is not None and re.match(
            r"^[0-9XYZ]", test.eidarout_net.netcode
        ):
            netcode = f"{test.eidarout_net.netcode}{test.eidarout_net.startdate.year}"
        else:
            netcode = (
                test.fdsn_net.netcode
                if test.fdsn_net is not None
                else (
                    test.xml_net.netcode
                    if test.xml_net is not None
                    else test.eidarout_net.netcode
                )
            )
        tests_data.append(
            {
                "test_time": test.test_time,
                "datacenter": test.xml_net.datacenter.name
                if test.xml_net is not None
                else (
                    test.eidarout_net.datacenter.name
                    if test.eidarout_net is not None
                    else "-"
                ),
                "network_code": netcode,
                "start_date": test.fdsn_net.startdate
                if test.fdsn_net is not None
                else (
                    test.xml_net.startdate
                    if test.xml_net is not None
                    else test.eidarout_net.startdate
                ),
                "doi": test.doi,
                "fdsn_net": bool(test.fdsn_net is not None),
                "xml_net": bool(test.xml_net is not None),
                "eidarout_net": bool(test.eidarout_net is not None),
                "page_works": test.page_works,
                "has_license": test.has_license,
                "xml_doi_match": test.xml_doi_match,
            }
        )

    return JsonResponse({"tests": tests_data})


# below view to show available test runs
def test_runs(request):
    datacenters = request.GET.get("datacenters", None)
    tests = Consistency.objects.filter_by_datacenter(datacenters).with_statistics()

    if datacenters is None:
        to_ret = render(
            request,
            "board/test_runs.html",
            {"unique_test_times": list(tests)},
        )
    else:
        to_ret = JsonResponse({"unique_test_times": list(tests)})

    return to_ret


# below view to show tests of specific datacenter
def datacenter_tests(request, datacenter_name):
    try:
        Datacenter.objects.get(name=datacenter_name)
    except Datacenter.DoesNotExist:
        return HttpResponse("<h1>Not Found</h1>Datacenter does not exist!", status=404)
    start_date = request.GET.get("start", None)
    end_date = request.GET.get("end", None)

    consistencies = Consistency.objects.filter(
        Q(xml_net__datacenter__name=datacenter_name)
        | Q(eidarout_net__datacenter__name=datacenter_name)
    )

    if not start_date and not end_date:
        latest_test_time = Consistency.objects.aggregate(
            latest_test_time=Max("test_time")
        )["latest_test_time"]
        consistencies = consistencies.filter(test_time=latest_test_time)
    else:
        if start_date:
            consistencies = consistencies.filter(test_time__gte=start_date)
        if end_date:
            consistencies = consistencies.filter(test_time__lte=end_date)

    consistency_data = []
    for consistency in consistencies:
        if consistency.xml_net is not None and re.match(
            r"^[0-9XYZ]", consistency.xml_net.netcode
        ):
            netcode = (
                f"{consistency.xml_net.netcode}{consistency.xml_net.startdate.year}"
            )
        elif consistency.eidarout_net is not None and re.match(
            r"^[0-9XYZ]", consistency.eidarout_net.netcode
        ):
            net = consistency.eidarout_net
            netcode = f"{net.netcode}{net.startdate.year}"
        else:
            netcode = (
                consistency.xml_net.netcode
                if consistency.xml_net is not None
                else consistency.eidarout_net.netcode
            )
        consistency_data.append(
            {
                "test_time": consistency.test_time,
                "network_code": netcode,
                "start_date": consistency.xml_net.startdate
                if consistency.xml_net is not None
                else consistency.eidarout_net.startdate,
                "doi": consistency.doi,
                "fdsn_net": bool(consistency.fdsn_net is not None),
                "xml_net": bool(consistency.xml_net is not None),
                "eidarout_net": bool(consistency.eidarout_net is not None),
                "page_works": consistency.page_works,
                "has_license": consistency.has_license,
                "xml_doi_match": consistency.xml_doi_match,
            }
        )

    context = {"datacenter_name": datacenter_name.upper(), "tests": consistency_data}
    return render(request, "board/datacenter_tests.html", context)


# function to tell if user is admin
def is_admin(user):
    return user.is_authenticated and user.is_staff


# below view can only be used by admin to run tests on will
@user_passes_test(is_admin)
def run_tests(request):
    try:
        current_time = timezone.now().replace(microsecond=0)
        consistency_from_FDSN(current_time)
        consistency_from_xml(current_time)
        consistency_from_routing(current_time)
    except Exception as e:
        traceback.print_exc()
        logger.exception()
        return HttpResponse(str(e), status=500)
    return HttpResponse(status=200)


def consistency_from_FDSN(current_time):
    logger.info("Making consistency checks starting from FDSN registry")
    for net in tqdm(Fdsn_registry.objects.all(), desc="Processing"):
        fdsn_end = (
            net.enddate
            if net.enddate is not None
            else datetime.datetime.strptime("2100-01-01", "%Y-%m-%d")
            .astimezone(datetime.timezone.utc)
            .date()
        )
        routings = Eida_routing.objects.filter(
            netcode=net.netcode, startdate__range=(net.startdate, fdsn_end)
        )
        datacite = Datacite.objects.filter(network=net).first()
        if datacite is None:
            page_works, has_license = None, None
        else:
            try:
                r = requests.get(datacite.page, timeout=10)
                page_works = bool(r.status_code == 200)
            except requests.exceptions.RequestException:
                page_works = False
            has_license = bool(datacite.licenses is not None)
        if not routings.exists():
            xmls = Stationxml.objects.filter(
                netcode=net.netcode, startdate__range=(net.startdate, fdsn_end)
            )
            if xmls.exists():
                for xml in xmls:
                    if net.doi is None:
                        doi_match = None
                    elif xml.doi is None:
                        doi_match = False
                    else:
                        doi_match = net.doi.lower() == xml.doi.lower()
                    Consistency(
                        test_time=current_time,
                        fdsn_net=net,
                        xml_net=xml,
                        doi=net.doi,
                        page_works=page_works,
                        has_license=has_license,
                        xml_doi_match=doi_match,
                    ).save()
            else:
                Consistency(
                    test_time=current_time,
                    fdsn_net=net,
                    doi=net.doi,
                    page_works=page_works,
                    has_license=has_license,
                ).save()
        else:
            for rout in routings:
                rout_end = (
                    rout.enddate
                    if rout.enddate is not None
                    else datetime.datetime.strptime("2100-01-01", "%Y-%m-%d")
                    .astimezone(datetime.timezone.utc)
                    .date()
                )
                start_search = min(rout.startdate, net.startdate)
                end_search = max(rout_end, fdsn_end)
                xml = Stationxml.objects.filter(
                    datacenter=rout.datacenter.name,
                    netcode=rout.netcode,
                    startdate__range=(start_search, end_search),
                ).first()
                if net.doi is None or xml is None:
                    doi_match = None
                elif xml.doi is None:
                    doi_match = False
                else:
                    doi_match = net.doi.lower() == xml.doi.lower()
                Consistency(
                    test_time=current_time,
                    fdsn_net=net,
                    eidarout_net=rout,
                    xml_net=xml if xml is not None else None,
                    doi=net.doi,
                    page_works=page_works,
                    has_license=has_license,
                    xml_doi_match=doi_match,
                ).save()


def consistency_from_xml(current_time):
    logger.info("Making consistency checks starting from StationXML files")
    unlinked_stationxml = Stationxml.objects.filter(
        ~Q(
            id__in=Consistency.objects.filter(test_time=current_time)
            .exclude(xml_net_id__isnull=True)
            .values_list("xml_net_id", flat=True)
        )
    )
    for net in tqdm(unlinked_stationxml, desc="Processing"):
        routings = Eida_routing.objects.filter(
            Q(
                netcode=net.netcode,
                startdate__lte=net.startdate,
                enddate__gte=net.startdate,
            )
            | Q(
                netcode=net.netcode,
                startdate__lte=net.startdate,
                enddate__isnull=True,
            )
        )
        if not routings.exists():
            Consistency(test_time=current_time, xml_net=net, doi=net.doi).save()
        for rout in routings:
            Consistency(
                test_time=current_time,
                xml_net=net,
                eidarout_net=rout,
                doi=net.doi,
            ).save()


def consistency_from_routing(current_time):
    logger.info("Making consistency checks starting from EIDA routing registry")
    unlinked_routing = Eida_routing.objects.filter(
        ~Q(
            id__in=Consistency.objects.filter(test_time=current_time)
            .exclude(eidarout_net_id__isnull=True)
            .values_list("eidarout_net_id", flat=True)
        )
    )
    for net in tqdm(unlinked_routing, desc="Processing"):
        Consistency(test_time=current_time, eidarout_net=net).save()


# below view can only be used by admin to update database on will
@user_passes_test(is_admin)
def update_db_from_sources(request):
    try:
        get_FDSN_networks()
        get_FDSN_datacenters()
        get_EIDA_routing()
    except Exception as e:
        traceback.print_exc()
        logger.exception()
        return HttpResponse(str(e), status=500)
    return HttpResponse(status=200)


def get_FDSN_networks():
    logger.info("Getting all networks from FDSN and updating database")
    r = requests.get("https://www.fdsn.org/ws/networks/1/query", timeout=20)
    for net in tqdm(r.json()["networks"], desc="Processing"):
        doi = net["doi"] if net["doi"] else None
        start = datetime.datetime.strptime(net["start_date"], "%Y-%m-%d").astimezone(
            datetime.timezone.utc
        )
        end = (
            datetime.datetime.strptime(net["end_date"], "%Y-%m-%d").astimezone(
                datetime.timezone.utc
            )
            if net["end_date"]
            else None
        )
        obj, created = Fdsn_registry.objects.update_or_create(
            netcode=net["fdsn_code"],
            startdate=start,
            defaults={"enddate": end, "doi": doi},
        )
        if net["doi"] != "":
            update_datacite_table(obj)


def update_datacite_table(net):
    dataciteapi = "https://api.datacite.org/application/vnd.datacite.datacite+json/"
    r = requests.get(dataciteapi + net.doi, timeout=20)
    datacite = r.json()
    licenses = datacite.get("rightsList") if datacite.get("rightsList") != [] else None
    publisher = datacite["publisher"].get("name") if "publisher" in datacite else None
    dateavail = None
    for d in datacite.get("dates", []):
        if d["dateType"] == "Available":
            if len(d["date"]) == 4:
                dateavail = d["date"] + "-01-01"
            else:
                dateavail = d["date"].split("/")[0]
    Datacite.objects.update_or_create(
        network=net,
        defaults={
            "licenses": licenses,
            "page": datacite.get("url"),
            "publisher": publisher,
            "date_available": dateavail,
        },
    )


def get_FDSN_datacenters():
    logger.info("Getting all datacenters from FDSN and updating database")
    r = requests.get("https://www.fdsn.org/ws/datacenters/1/query", timeout=20)
    for dc in tqdm(r.json()["datacenters"], desc="Processing"):
        station_url = None
        for r in dc["repositories"]:
            for s in r["services"]:
                if s["name"] == "fdsnws-station-1":
                    station_url = s["url"]
        datacenter = Datacenter(
            name=dc["name"],
            station_url=urlparse(station_url).netloc
            if station_url is not None
            else None,
        )
        datacenter.save()
        if dc["name"] in [
            "GEOFON",
            "ODC",
            "ETH",
            "RESIF",
            "INGV",
            "LMU",
            "ICGC",
            "NOA",
            "BGR",
            "NIEP",
            "KOERI",
            "UIB-NORSAR",
        ]:
            update_stationxml_table(datacenter)


def update_stationxml_table(datacenter):
    try:
        r = requests.get(
            f"https://{datacenter.station_url}/fdsnws/station/1/query?level=network",
            timeout=20,
        )
        root = ET.fromstring(r.text)
    except Exception:
        return
    namespace = {"ns": "http://www.fdsn.org/xml/station/1"}
    networks = root.findall("./ns:Network", namespaces=namespace)
    for n in networks:
        try:
            net_start = (
                datetime.datetime.strptime(n.attrib["startDate"], "%Y-%m-%dT%H:%M:%S")
                .astimezone(datetime.timezone.utc)
                .date()
            )
        except ValueError:
            try:
                net_start = (
                    datetime.datetime.strptime(
                        n.attrib["startDate"], "%Y-%m-%dT%H:%M:%SZ"
                    )
                    .astimezone(datetime.timezone.utc)
                    .date()
                )
            except ValueError:
                try:
                    net_start = (
                        datetime.datetime.strptime(
                            n.attrib["startDate"], "%Y-%m-%dT%H:%M:%S.%f"
                        )
                        .astimezone(datetime.timezone.utc)
                        .date()
                    )
                except ValueError:
                    try:
                        net_start = (
                            datetime.datetime.strptime(
                                n.attrib["startDate"], "%Y-%m-%dT%H:%M:%S.%fZS"
                            )
                            .astimezone(datetime.timezone.utc)
                            .date()
                        )
                    except ValueError:
                        net_start = n.attrib["startDate"][:10]
        try:
            net_end = (
                datetime.datetime.strptime(
                    n.attrib.get("endDate"), "%Y-%m-%dT%H:%M:%S"
                )
                .astimezone(datetime.timezone.utc)
                .date()
            )
        except ValueError:
            try:
                net_end = (
                    datetime.datetime.strptime(
                        n.attrib.get("endDate"), "%Y-%m-%dT%H:%M:%SZ"
                    )
                    .astimezone(datetime.timezone.utc)
                    .date()
                )
            except ValueError:
                try:
                    net_end = (
                        datetime.datetime.strptime(
                            n.attrib.get("endDate"), "%Y-%m-%dT%H:%M:%S.%f"
                        )
                        .astimezone(datetime.timezone.utc)
                        .date()
                    )
                except ValueError:
                    try:
                        net_end = (
                            datetime.datetime.strptime(
                                n.attrib.get("endDate"), "%Y-%m-%dT%H:%M:%S.%fZS"
                            )
                            .astimezone(datetime.timezone.utc)
                            .date()
                        )
                    except ValueError:
                        try:
                            net_end = n.attrib.get("endDate")[:10]
                        except ValueError:
                            net_end = None
        doi = n.find("./ns:Identifier", namespaces=namespace)
        doi = doi.text if doi is not None and len(doi.text) < 100 else None
        Stationxml.objects.update_or_create(
            datacenter=datacenter,
            netcode=n.attrib["code"],
            startdate=net_start,
            defaults={
                "enddate": net_end,
                "doi": doi,
                "restriction": n.attrib.get("restrictedStatus"),
            },
        )


def get_EIDA_routing():
    logger.info("Getting EIDA routing information")
    r = requests.get(
        "https://www.orfeus-eu.org/eidaws/routing/1/query?format=json&service=station",
        timeout=20,
    )
    for dc in tqdm(r.json(), desc="Processing"):
        # get datacenter from database
        datacenter = Datacenter.objects.get(station_url=urlparse(dc["url"]).netloc)
        for net in dc["params"]:
            try:
                net_start = (
                    datetime.datetime.strptime(net["start"], "%Y-%m-%dT%H:%M:%S")
                    .astimezone(datetime.timezone.utc)
                    .date()
                )
            except ValueError:
                net_start = (
                    datetime.datetime.strptime(net["start"], "%Y-%m-%dT%H:%M:%S.%f")
                    .astimezone(datetime.timezone.utc)
                    .date()
                )
            try:
                net_end = (
                    datetime.datetime.strptime(net["end"], "%Y-%m-%dT%H:%M:%S")
                    .astimezone(datetime.timezone.utc)
                    .date()
                )
            except ValueError:
                try:
                    net_end = (
                        datetime.datetime.strptime(net["end"], "%Y-%m-%dT%H:%M:%S.%f")
                        .astimezone(datetime.timezone.utc)
                        .date()
                    )
                except ValueError:
                    net_end = None
            Eida_routing.objects.update_or_create(
                netcode=net["net"],
                datacenter=datacenter,
                startdate=net_start,
                defaults={"enddate": net_end, "priority": net["priority"]},
            )
