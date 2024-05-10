from django.test import TestCase
from django.utils import timezone

from .models import Test, Network, Datacenter, Routing, Datacite, Stationxml


class TestModelTests(TestCase):
    def test_stationxml_doi_match_true(self):
        """
        xml_doi_match is True if doi in Stationxml and Network tables match
        """
        net = Network(code='TN', startdate="2024-01-01", doi="some_doi")
        net.save()
        Stationxml(network=net, doi="some_doi").save()
        testnet = Test(test_time=timezone.now(), network=net, xml_doi_match=net.doi==Stationxml.objects.filter(network__code=net.code)[0].doi)
        self.assertIs(testnet.xml_doi_match, True)

    def test_stationxml_doi_match_false(self):
        """
        xml_doi_match is False if doi in Stationxml and Network tables do not match
        """
        net = Network(code='TN', startdate="2024-01-01", doi="some_doi")
        net.save()
        Stationxml(network=net, doi="some_other_doi").save()
        testnet = Test(test_time=timezone.now(), network=net, xml_doi_match=net.doi==Stationxml.objects.filter(network__code=net.code)[0].doi)
        self.assertIs(testnet.xml_doi_match, False)

    def test_stationxml_doi_match_nonexistent(self):
        """
        xml_doi_match is False if doi in Stationxml does not exist
        """
        net = Network(code='TN', startdate="2024-01-01", doi="some_doi")
        net.save()
        Stationxml(network=net).save()
        testnet = Test(test_time=timezone.now(), network=net, xml_doi_match=net.doi==Stationxml.objects.filter(network__code=net.code)[0].doi)
        self.assertIs(testnet.xml_doi_match, False)
