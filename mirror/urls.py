from django.urls import path
from mirror import views

app_name = 'mirror'

urlpatterns = [
    path('', views.index, name='index'),
]
