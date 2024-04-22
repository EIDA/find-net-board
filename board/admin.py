from django.contrib import admin

from .models import Network, Test, Routing, Datacenter, Datacite, Stationxml

class NetworkAdmin(admin.ModelAdmin):
    search_fields = ['code']

class DatacenterAdmin(admin.ModelAdmin):
    search_fields = ['name']

class DataciteAdmin(admin.ModelAdmin):
    search_fields = ['network__code']

class RoutingAdmin(admin.ModelAdmin):
    search_fields = ['datacenter__name', 'network__code']

class StationxmlAdmin(admin.ModelAdmin):
    search_fields = ['network__code']

class TestAdmin(admin.ModelAdmin):
    search_fields = ['network__code']

admin.site.register(Network, NetworkAdmin)
admin.site.register(Test, TestAdmin)
admin.site.register(Routing, RoutingAdmin)
admin.site.register(Datacenter, DatacenterAdmin)
admin.site.register(Datacite, DataciteAdmin)
admin.site.register(Stationxml, StationxmlAdmin)
