from celery import shared_task, chain
from django.utils import timezone

from .views import (
    get_FDSN_networks,
    get_FDSN_datacenters,
    get_EIDA_routing,
    consistency_from_FDSN,
    consistency_from_xml,
    consistency_from_routing,
)


@shared_task
def update_db():
    get_FDSN_networks()
    get_FDSN_datacenters()
    get_EIDA_routing()


@shared_task
def tests_run():
    current_time = timezone.now().replace(microsecond=0)
    consistency_from_FDSN(current_time)
    consistency_from_xml(current_time)
    consistency_from_routing(current_time)


@shared_task
def update_db_and_run_tests():
    chain(update_db.si(), tests_run.si()).apply_async()
