import os
import sys

INTERP = os.path.join(os.path.dirname(__file__), "venv", "bin", "python3")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simple_mirror.settings')

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
