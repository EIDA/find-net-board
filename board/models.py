from django.db import models
from django.db.models import Count, Case, When, F, ExpressionWrapper, FloatField, Q


class Fdsn_registry(models.Model):
    netcode = models.CharField(max_length=10, null=False)
    startdate = models.DateField(null=False)
    enddate = models.DateField(null=True, blank=True)
    doi = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["netcode", "startdate"], name="unique_combination_fdsn_registry"
            )
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
        return (
            f"({self.network.netcode}, {self.network.startdate}, "
            f"{self.licenses}, {self.page}, {self.publisher}, {self.date_available})"
        )


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
            models.UniqueConstraint(
                fields=["netcode", "datacenter", "startdate"],
                name="unique_combination_eida_routing",
            )
        ]

    def __str__(self):
        return (
            f"({self.netcode}, {self.datacenter.name}, {self.startdate}, "
            f"{self.enddate}, {self.priority})"
        )


class Stationxml(models.Model):
    datacenter = models.ForeignKey(Datacenter, on_delete=models.CASCADE)
    netcode = models.CharField(max_length=10, null=False)
    startdate = models.DateField(null=False)
    enddate = models.DateField(null=True, blank=True)
    doi = models.CharField(max_length=100, null=True, blank=True)
    restriction = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["datacenter", "netcode", "startdate"],
                name="unique_combination_stationxml",
            )
        ]

    def __str__(self):
        return (
            f"({self.datacenter.name}, {self.netcode}, {self.startdate}, "
            f"{self.enddate}, {self.doi}, {self.restriction})"
        )


class ConsistencyQuerySet(models.QuerySet):
    def with_statistics(self):
        return (
            self.values("test_time")
            .annotate(
                count=Count("test_time"),
                true_page_count=Count(Case(When(page_works=True, then=1))),
                true_license_count=Count(Case(When(has_license=True, then=1))),
                true_xml_doi_match_count=Count(Case(When(xml_doi_match=True, then=1))),
                null_fdsn_net_count=Count(Case(When(fdsn_net__isnull=False, then=1))),
                null_xml_net_count=Count(Case(When(xml_net__isnull=False, then=1))),
                null_eidarout_net_count=Count(
                    Case(When(eidarout_net__isnull=False, then=1))
                ),
            )
            .annotate(
                true_page_percentage=ExpressionWrapper(
                    (F("true_page_count") * 100.0) / F("count"),
                    output_field=FloatField(),
                ),
                true_license_percentage=ExpressionWrapper(
                    (F("true_license_count") * 100.0) / F("count"),
                    output_field=FloatField(),
                ),
                true_xml_doi_match_percentage=ExpressionWrapper(
                    (F("true_xml_doi_match_count") * 100.0) / F("count"),
                    output_field=FloatField(),
                ),
                null_fdsn_net_percentage=ExpressionWrapper(
                    (F("null_fdsn_net_count") * 100.0) / F("count"),
                    output_field=FloatField(),
                ),
                null_xml_net_percentage=ExpressionWrapper(
                    (F("null_xml_net_count") * 100.0) / F("count"),
                    output_field=FloatField(),
                ),
                null_eidarout_net_percentage=ExpressionWrapper(
                    (F("null_eidarout_net_count") * 100.0) / F("count"),
                    output_field=FloatField(),
                ),
            )
            .order_by("-test_time")
        )

    def filter_by_datacenter(self, datacenters):
        if datacenters == "eida":
            return self.filter(Q(xml_net__isnull=False) | Q(eidarout_net__isnull=False))
        elif datacenters == "non-eida":
            return self.filter(Q(xml_net__isnull=True) & Q(eidarout_net__isnull=True))
        return self


class ConsistencyManager(models.Manager):
    def get_queryset(self):
        return ConsistencyQuerySet(self.model, using=self._db)

    def with_statistics(self):
        return self.get_queryset().with_statistics()

    def filter_by_datacenter(self, datacenters):
        return self.get_queryset().filter_by_datacenter(datacenters)


class Consistency(models.Model):
    test_time = models.DateTimeField(null=False)
    fdsn_net = models.ForeignKey(
        Fdsn_registry, on_delete=models.SET_NULL, null=True, blank=True
    )
    eidarout_net = models.ForeignKey(
        Eida_routing, on_delete=models.SET_NULL, null=True, blank=True
    )
    xml_net = models.ForeignKey(
        Stationxml, on_delete=models.SET_NULL, null=True, blank=True
    )
    doi = models.CharField(max_length=100, null=True, blank=True)
    page_works = models.BooleanField(null=True, blank=True)
    has_license = models.BooleanField(null=True, blank=True)
    xml_doi_match = models.BooleanField(null=True, blank=True)

    objects = ConsistencyManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["test_time", "fdsn_net", "eidarout_net", "xml_net"],
                name="unique_combination_consistency",
            )
        ]

    def __str__(self):
        fdsn_net_str = (
            f"{self.fdsn_net.netcode}-{self.fdsn_net.startdate.year}"
            if self.fdsn_net is not None
            else None
        )
        eidarout_net_str = (
            f"{self.eidarout_net.netcode}-{self.eidarout_net.startdate.year}"
            if self.eidarout_net is not None
            else None
        )
        xml_net_str = (
            f"{self.xml_net.netcode}-{self.xml_net.startdate.year}"
            if self.xml_net is not None
            else None
        )
        return (
            f"({self.test_time}, {fdsn_net_str}, {eidarout_net_str}, "
            f"{xml_net_str}, {self.doi}, {self.page_works}, "
            f"{self.has_license}, {self.xml_doi_match})"
        )
