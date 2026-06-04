from django.urls import path
from . import views

app_name = 'mirror'

urlpatterns = [
    path('', views.index, name='index'),
]
