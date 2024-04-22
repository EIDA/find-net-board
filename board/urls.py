from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path('admin/update_db_from_sources/', views.update_db_from_sources, name='admin_update_sources'),
    path('admin/run_tests/', views.run_tests, name='admin_run_tests'),
]
