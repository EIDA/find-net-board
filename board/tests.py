import requests
from django.test import TestCase
from django.utils import timezone

from .models import (
    Consistency,
    Datacenter,
    Fdsn_registry,
    Stationxml,
)


class TestModelConsistency(TestCase):
    def test_page_works(self):
        """
        test that a page of an fdsn network works
        """
        try:
            r = requests.get("https://www.fdsn.org/networks/detail/HL/", timeout=20)
            page_works = bool(r.status_code == 200)
        except requests.exceptions.RequestException:
            page_works = False
        self.assertIs(page_works, True)

    def test_page_not_work(self):
        """
        test that a page of an fdsn network does not work
        """
        try:
            r = requests.get(
                "https://www.fdsn.org/networks/detail/NONEXISTENTNETWORK/", timeout=20
            )
            page_works = bool(r.status_code == 200)
        except requests.exceptions.RequestException:
            page_works = False
        self.assertIs(page_works, False)

    def test_stationxml_doi_match_true(self):
        """
        xml_doi_match is True if doi in Stationxml and Network tables match
        """
        net = Fdsn_registry(netcode="TN", startdate="2024-01-01", doi="some_doi")
        net.save()
        dc = Datacenter(name="DC")
        dc.save()
        xml = Stationxml(
            datacenter=dc, netcode="TN", startdate="2024-01-01", doi="some_doi"
        )
        xml.save()
        testnet = Consistency(
            test_time=timezone.now(),
            fdsn_net=net,
            xml_net=xml,
            xml_doi_match=net.doi
            == Stationxml.objects.filter(netcode=net.netcode, startdate=net.startdate)
            .first()
            .doi,
        )
        self.assertIs(testnet.xml_doi_match, True)

    def test_stationxml_doi_match_false(self):
        """
        xml_doi_match is False if doi in Stationxml and Network tables do not match
        """
        net = Fdsn_registry(netcode="TN", startdate="2024-01-01", doi="some_doi")
        net.save()
        dc = Datacenter(name="DC")
        dc.save()
        xml = Stationxml(
            datacenter=dc, netcode="TN", startdate="2024-01-01", doi="some_other_doi"
        )
        xml.save()
        testnet = Consistency(
            test_time=timezone.now(),
            fdsn_net=net,
            xml_net=xml,
            xml_doi_match=net.doi
            == Stationxml.objects.filter(netcode=net.netcode, startdate=net.startdate)
            .first()
            .doi,
        )
        self.assertIs(testnet.xml_doi_match, False)

    def test_stationxml_doi_match_nonexistent(self):
        """
        xml_doi_match is False if doi in Stationxml does not exist
        """
        net = Fdsn_registry(netcode="TN", startdate="2024-01-01", doi="some_doi")
        net.save()
        dc = Datacenter(name="DC")
        dc.save()
        xml = Stationxml(datacenter=dc, netcode="TN", startdate="2024-01-01")
        xml.save()
        testnet = Consistency(
            test_time=timezone.now(),
            fdsn_net=net,
            xml_net=xml,
            xml_doi_match=net.doi
            == Stationxml.objects.filter(netcode=net.netcode, startdate=net.startdate)
            .first()
            .doi,
        )
        self.assertIs(testnet.xml_doi_match, False)
