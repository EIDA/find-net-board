import logging
from datetime import datetime
from urllib.parse import urlparse

import requests
from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from .views import update_datacite_table, update_stationxml_table
from .models import (
    Consistency,
    Datacenter,
    Datacite,
    Eida_routing,
    Fdsn_registry,
    Stationxml,
)

logger = logging.getLogger(__name__)


@shared_task
def update_and_run():
    logger.info("Getting all networks from FDSN and updating database")
    r = requests.get("https://www.fdsn.org/ws/networks/1/query", timeout=20)
    for net in r.json()["networks"]:
        doi = net["doi"] if net["doi"] else None
        start = datetime.strptime(net["start_date"], "%Y-%m-%d").astimezone(
            datetime.timezone.utc
        )
        end = (
            datetime.strptime(net["end_date"], "%Y-%m-%d").astimezone(
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

    logger.info("Getting all datacenters from FDSN and updating database")
    r = requests.get("https://www.fdsn.org/ws/datacenters/1/query", timeout=20)
    for dc in r.json()["datacenters"]:
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

    logger.info("Getting EIDA routing information")
    r = requests.get(
        "https://www.orfeus-eu.org/eidaws/routing/1/query?format=json&service=station",
        timeout=20,
    )
    for dc in r.json():
        # get datacenter from database
        datacenter = Datacenter.objects.get(station_url=urlparse(dc["url"]).netloc)
        for net in dc["params"]:
            try:
                net_start = (
                    datetime.strptime(net["start"], "%Y-%m-%dT%H:%M:%S")
                    .astimezone(datetime.timezone.utc)
                    .date()
                )
            except Exception:
                net_start = (
                    datetime.strptime(net["start"], "%Y-%m-%dT%H:%M:%S.%f")
                    .astimezone(datetime.timezone.utc)
                    .date()
                )
            try:
                net_end = (
                    datetime.strptime(net["end"], "%Y-%m-%dT%H:%M:%S")
                    .astimezone(datetime.timezone.utc)
                    .date()
                )
            except Exception:
                try:
                    net_end = (
                        datetime.strptime(net["end"], "%Y-%m-%dT%H:%M:%S.%f")
                        .astimezone(datetime.timezone.utc)
                        .date()
                    )
                except Exception:
                    net_end = None
            Eida_routing.objects.update_or_create(
                netcode=net["net"],
                datacenter=datacenter,
                startdate=net_start,
                defaults={"enddate": net_end, "priority": net["priority"]},
            )
    logger.info("Finished updating DB from sources")

    logger.info("Checking consistency for each available network")
    current_time = timezone.now().replace(microsecond=0)
    # starting from Fdsn_registry table
    logger.info("Making consistency checks starting from FDSN registry")
    for net in Fdsn_registry.objects.all():
        fdsn_end = (
            net.enddate
            if net.enddate is not None
            else datetime.strptime("2100-01-01", "%Y-%m-%d")
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
                    else datetime.strptime("2100-01-01", "%Y-%m-%d")
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
    # starting from Stationxml table
    logger.info("Making consistency checks starting from StationXML files")
    unlinked_stationxml = Stationxml.objects.filter(
        ~Q(
            id__in=Consistency.objects.filter(test_time=current_time).values_list(
                "xml_net_id", flat=True
            )
        )
    )
    for net in unlinked_stationxml:
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
                test_time=current_time, xml_net=net, eidarout_net=rout, doi=net.doi
            ).save()
    # starting from Eida_routing table
    logger.info("Making consistency checks starting from EIDA routing registry")
    unlinked_routing = Eida_routing.objects.filter(
        ~Q(
            id__in=Consistency.objects.filter(test_time=current_time).values_list(
                "eidarout_net_id", flat=True
            )
        )
    )
    for net in unlinked_routing:
        Consistency(test_time=current_time, eidarout_net=net).save()
    logger.info("Finished running tests for all networks")
