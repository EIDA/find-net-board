from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from django.http import HttpResponse

from .models import Test, Network, Datacenter

import requests
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# main home page view
def index(request):
    tests = Test.objects.order_by("-test_time")
    context = {"tests": tests}
    return render(request, "board/index.html", context)


# below view can only be used by admin to update database and run tests on will
def is_admin(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_admin)
def update_db_from_sources(request):
    datacenters_datasets, datacenters_urls = get_FDSN_datacenters()
    #eida_routing = get_EIDA_routing()
    #process_networks()
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
