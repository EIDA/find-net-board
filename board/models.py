from django.db import models


class Fdsn_registry(models.Model):
    netcode = models.CharField(max_length=10, null=False)
    startdate = models.DateField(null=False)
    enddate = models.DateField(null=True, blank=True)
    doi = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['netcode', 'startdate'], name='unique_combination_fdsn_registry')
        ]

    def __str__(self):
        return f"({self.netcode}, {self.startdate}, {self.enddate}, {self.doi})"


class Datacite(models.Model):
    network = models.ForeignKey(Fdsn_registry, on_delete=models.CASCADE)
    licenses = models.JSONField(null=True, blank=True)
    page = models.CharField(max_length=300, null=True, blank=True)
    publisher = models.CharField(max_length=300, null=True, blank=True)
    date_available = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"({self.network.netcode}, {self.network.startdate}, {self.licenses}, {self.page}, {self.publisher}, {self.date_available})"


class Datacenter(models.Model):
    name = models.CharField(max_length=30, primary_key=True)
    station_url = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f"({self.name}, {self.station_url})"


class Eida_routing(models.Model):
    netcode = models.CharField(max_length=10, null=False)
    datacenter = models.ForeignKey(Datacenter, on_delete=models.CASCADE)
    startdate = models.DateField(null=False)
    enddate = models.DateField(null=True, blank=True)
    priority = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['netcode', 'datacenter', 'startdate'], name='unique_combination_eida_routing')
        ]

    def __str__(self):
        return f"({self.netcode}, {self.datacenter.name}, {self.startdate}, {self.enddate}, {self.priority})"


class Stationxml(models.Model):
    datacenter = models.ForeignKey(Datacenter, on_delete=models.CASCADE)
    netcode = models.CharField(max_length=10, null=False)
    startdate = models.DateField(null=False)
    enddate = models.DateField(null=True, blank=True)
    doi = models.CharField(max_length=100, null=True, blank=True)
    restriction = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['datacenter', 'netcode', 'startdate'], name='unique_combination_stationxml')
        ]

    def __str__(self):
        return f"({self.datacenter.name}, {self.netcode}, {self.startdate}, {self.enddate}, {self.doi}, {self.restriction})"


class Consistency(models.Model):
    test_time = models.DateTimeField(null=False)
    fdsn_net = models.ForeignKey(Fdsn_registry, on_delete=models.SET_NULL, null=True, blank=True)
    eidarout_net = models.ForeignKey(Eida_routing, on_delete=models.SET_NULL, null=True, blank=True)
    xml_net = models.ForeignKey(Stationxml, on_delete=models.SET_NULL, null=True, blank=True)
    doi = models.CharField(max_length=100, null=True, blank=True)
    page_works = models.BooleanField(null=True, blank=True)
    has_license = models.BooleanField(null=True, blank=True)
    xml_doi_match = models.BooleanField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['test_time', 'fdsn_net', 'eidarout_net', 'xml_net'], name='unique_combination_consistency')
        ]

    def __str__(self):
        return f"({self.test_time}, {self.fdsn_net.netcode if self.fdsn_net is not None else None}, {self.eidarout_net.netcode if self.eidarout_net is not None else None}, {self.xml_net.netcode if self.xml_net is not None else None}, {self.doi}, {self.page_works}, {self.has_license}, {self.xml_doi_match})"
