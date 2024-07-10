from django.contrib import admin

from .models import (
    Consistency,
    Datacenter,
    Datacite,
    Eida_routing,
    Fdsn_registry,
    Stationxml,
)


class Fdsn_registryAdmin(admin.ModelAdmin):
    search_fields = ["netcode"]


class DatacenterAdmin(admin.ModelAdmin):
    search_fields = ["name"]


class DataciteAdmin(admin.ModelAdmin):
    search_fields = ["network__netcode"]


class Eida_routingAdmin(admin.ModelAdmin):
    search_fields = ["datacenter__name", "netcode"]


class StationxmlAdmin(admin.ModelAdmin):
    search_fields = ["datacenter__name", "netcode"]


class ConsistencyAdmin(admin.ModelAdmin):
    search_fields = ["fdsn_net__netcode", "eidarout_net__netcode", "xml_net__netcode"]


admin.site.register(Fdsn_registry, Fdsn_registryAdmin)
admin.site.register(Consistency, ConsistencyAdmin)
admin.site.register(Eida_routing, Eida_routingAdmin)
admin.site.register(Datacenter, DatacenterAdmin)
admin.site.register(Datacite, DataciteAdmin)
admin.site.register(Stationxml, StationxmlAdmin)
