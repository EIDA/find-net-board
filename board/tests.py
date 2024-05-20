from django.test import TestCase
from django.utils import timezone
import requests

from .models import Fdsn_registry, Consistency, Eida_routing, Datacenter, Datacite, Stationxml


class TestModelTests(TestCase):
    def test_page_works(self):
        """
        test that a page of an fdsn network works
        """
        try:
            r = requests.get("https://www.fdsn.org/networks/detail/HL/")
            page_works = True if r.status_code == 200 else False
        except Exception:
            page_works = False
        self.assertIs(page_works, True)

    def test_page_not_work(self):
        """
        test that a page of an fdsn network does not work
        """
        try:
            r = requests.get("https://www.fdsn.org/networks/detail/NONEXISTENTNETWORK/")
            page_works = True if r.status_code == 200 else False
        except Exception:
            page_works = False
        self.assertIs(page_works, False)

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

    def test_stationxml_restriction_match_true_with_license(self):
        """
        xml_restriction_match is True if network has license and restriction status in xml is open/partial
        """
        net = Network(code='TN', startdate="2024-01-01")
        net.save()
        Datacite(network=net, licenses="some_license1, some_license2").save()
        Stationxml(network=net, restriction="open").save()
        lic = True if Datacite.objects.filter(network__code=net.code)[0].licenses else False
        restr = Stationxml.objects.filter(network__code=net.code)[0].restriction
        testnet = Test(test_time=timezone.now(), network=net, xml_restriction_match=lic==(restr in ["open", "partial"]))
        self.assertIs(testnet.xml_restriction_match, True)

    def test_stationxml_restriction_match_true_without_license(self):
        """
        xml_restriction_match is True if network does not have license and restriction status in xml is anything but open/partial
        """
        net = Network(code='TN', startdate="2024-01-01")
        net.save()
        Datacite(network=net).save()
        Stationxml(network=net, restriction="restricted").save()
        lic = True if Datacite.objects.filter(network__code=net.code)[0].licenses else False
        restr = Stationxml.objects.filter(network__code=net.code)[0].restriction
        testnet = Test(test_time=timezone.now(), network=net, xml_restriction_match=lic==(restr in ["open", "partial"]))
        self.assertIs(testnet.xml_restriction_match, True)

    def test_stationxml_restriction_match_false_without_license(self):
        """
        xml_restriction_match is False if network does not have license and restriction status in xml is open/partial
        """
        net = Network(code='TN', startdate="2024-01-01")
        net.save()
        Datacite(network=net).save()
        Stationxml(network=net, restriction="open").save()
        lic = True if Datacite.objects.filter(network__code=net.code)[0].licenses else False
        restr = Stationxml.objects.filter(network__code=net.code)[0].restriction
        testnet = Test(test_time=timezone.now(), network=net, xml_restriction_match=lic==(restr in ["open", "partial"]))
        self.assertIs(testnet.xml_restriction_match, False)

    def test_stationxml_restriction_match_false_with_license(self):
        """
        xml_restriction_match is False if network has license and restriction status in xml is anything but open/partial
        """
        net = Network(code='TN', startdate="2024-01-01")
        net.save()
        Datacite(network=net, licenses="some_license1, some_license2").save()
        Stationxml(network=net, restriction="restricted").save()
        lic = True if Datacite.objects.filter(network__code=net.code)[0].licenses else False
        restr = Stationxml.objects.filter(network__code=net.code)[0].restriction
        testnet = Test(test_time=timezone.now(), network=net, xml_restriction_match=lic==(restr in ["open", "partial"]))
        self.assertIs(testnet.xml_restriction_match, False)
