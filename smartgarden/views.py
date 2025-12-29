from django.http import HttpResponse

def health(request):
    """Simple healthcheck endpoint used by containers and load balancers.

    Returns HTTP 200 with a short body when the app is reachable.
    Keep this lightweight: no DB queries here.
    """
    return HttpResponse("ok", content_type="text/plain")
