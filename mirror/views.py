from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def index(request: HttpRequest) -> HttpResponse:
    """Render the webcam mirror page.

    Args:
        request: Incoming HTTP request.

    Returns:
        Rendered mirror index page.
    """
    return render(request, 'mirror/index.html')
