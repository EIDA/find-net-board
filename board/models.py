from django.db import models


class Network(models.Model):
    code = models.CharField(max_length=10, null=False)
    startdate = models.DateField(null=False)
    enddate = models.DateField(null=True)
    doi = models.CharField(max_length=100, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'startdate'], name='unique_combination_network')
        ]

    def __str__(self):
        return f"({self.code}, {self.startdate}, {self.enddate}, {self.doi})"


class Datacite(models.Model):
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    licenses = models.CharField(max_length=500, null=True)
    page = models.CharField(max_length=300, null=True)
    publisher = models.CharField(max_length=300, null=True)

    def __str__(self):
        return f"({self.network.code}, {self.network.startdate}, {self.licenses}, {self.page}, {self.publisher})"


class Datacenter(models.Model):
    name = models.CharField(max_length=30, primary_key=True)
    station_url = models.CharField(max_length=300, null=True)

    def __str__(self):
        return f"({self.name}, {self.station_url})"


class Routing(models.Model):
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    datacenter = models.ForeignKey(Datacenter, on_delete=models.CASCADE)
    priority = models.IntegerField(null=True)
    source = models.CharField(max_length=4, choices=[('EIDA', 'EIDA'), ('FDSN', 'FDSN')], null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['network', 'datacenter'], name='unique_combination_routing')
        ]

    def __str__(self):
        return f"({self.network.code}, {self.network.startdate}, {self.datacenter.name}, {self.priority}, {self.source})"


class Stationxml(models.Model):
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    doi = models.CharField(max_length=100, null=True)
    restriction = models.CharField(max_length=50, null=True)

    def __str__(self):
        return f"({self.network.code}, {self.network.startdate}, {self.doi}, {self.restriction})"


class Test(models.Model):
    test_time = models.DateTimeField(null=False)
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    doi = models.CharField(max_length=100, null=True)
    page_works = models.BooleanField(null=True)
    has_license = models.BooleanField(null=True)
    xml_doi_match = models.BooleanField(null=True)
    xml_restriction_match = models.BooleanField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['test_time', 'network'], name='unique_combination_test')
        ]

    def __str__(self):
        return f"({self.test_time}, {self.network.code}, {self.network.startdate}, {self.doi}, {self.page_works}, {self.has_license}, {self.xml_doi_match}, {self.xml_restriction_match})"
