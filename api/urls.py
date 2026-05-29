from django.urls import path

from api import views

urlpatterns = [
    path('hook', views.hook, name='hook')
]