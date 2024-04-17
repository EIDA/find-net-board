from django.shortcuts import render

from .models import Test

def index(request):
    latest_tests = Test.objects.order_by("-test_time")[:100]
    context = {"latest_tests": latest_tests}
    return render(request, "board/index.html", context)
