from celery import shared_task

from .models import Network

@shared_task
def learn():
    print("I learned celery!!!")
    print(Network.objects.first())
