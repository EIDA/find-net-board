from django.contrib import admin

from .models import Fdsn_registry, Consistency, Eida_routing, Datacenter, Datacite, Stationxml

class Fdsn_registryAdmin(admin.ModelAdmin):
    search_fields = ['netcode']

class DatacenterAdmin(admin.ModelAdmin):
    search_fields = ['name']

class DataciteAdmin(admin.ModelAdmin):
    search_fields = ['network__netcode']

class Eida_routingAdmin(admin.ModelAdmin):
    search_fields = ['datacenter__name', 'netcode']

class StationxmlAdmin(admin.ModelAdmin):
    search_fields = ['datacenter__name', 'netcode']

class ConsistencyAdmin(admin.ModelAdmin):
    search_fields = ['fdsn_net', 'eidarout_net', 'xml_net']

admin.site.register(Fdsn_registry, Fdsn_registryAdmin)
admin.site.register(Consistency, ConsistencyAdmin)
admin.site.register(Eida_routing, Eida_routingAdmin)
admin.site.register(Datacenter, DatacenterAdmin)
admin.site.register(Datacite, DataciteAdmin)
admin.site.register(Stationxml, StationxmlAdmin)
