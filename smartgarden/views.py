from django.db import DatabaseError, connection
from django.http import HttpResponse

def health(request):
    """Simple healthcheck endpoint used by containers and load balancers.

    Returns HTTP 200 with a short body when the app is reachable.
    Keep this lightweight: no DB queries here.
    """
    return HttpResponse("ok", content_type="text/plain")


def readiness(request):
    """Readiness check that verifies the configured database is reachable."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return HttpResponse("database unavailable", status=503, content_type="text/plain")

    return HttpResponse("ready", content_type="text/plain")
