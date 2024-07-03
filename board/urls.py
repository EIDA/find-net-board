from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("tests/", views.test_runs, name="tests_runs"),
    path("search_tests/", views.search_tests, name="search_tests"),
    path(
        "datacenter/<str:datacenter_name>/",
        views.datacenter_tests,
        name="datacenter_tests",
    ),
    path(
        "admin/update_db_from_sources/",
        views.update_db_from_sources,
        name="admin_update_sources",
    ),
    path("admin/run_tests/", views.run_tests, name="admin_run_tests"),
]
