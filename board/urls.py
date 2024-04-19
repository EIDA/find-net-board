from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path('admin/update_db_from_sources/', views.update_db_from_sources, name='execute_custom_action'),
]
