from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("acquisition/simulate/", views.simulate_acquisition, name="simulate_acquisition"),
    path("guest/<uuid:lead_id>/", views.guest_chat, name="guest_chat"),
    path("guest/<uuid:lead_id>/send/", views.guest_send, name="guest_send"),
    path("guest/<uuid:lead_id>/continue/", views.trust_transition, name="trust_transition"),
    path("guest/<uuid:lead_id>/convert/", views.convert, name="convert"),
    path("patient/<uuid:session_id>/", views.patient_chat, name="patient_chat"),
    path("patient/<uuid:session_id>/send/", views.patient_send, name="patient_send"),
]
