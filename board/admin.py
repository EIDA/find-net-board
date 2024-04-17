from django.contrib import admin

from .models import Network, Test, Routing, Datacenter, Datacite, Stationxml

admin.site.register(Network)
admin.site.register(Test)
admin.site.register(Routing)
admin.site.register(Datacenter)
admin.site.register(Datacite)
admin.site.register(Stationxml)
