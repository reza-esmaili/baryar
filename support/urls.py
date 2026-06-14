from django.urls import path
from . import views

urlpatterns = [
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/create/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("ajax/topics/", views.load_topics, name="ajax_topics"),
    path("agent/", views.agent_dashboard, name="agent_dashboard"),
    path("tickets/<int:pk>/transfer/", views.ticket_transfer, name="ticket_transfer"),
    path(
    "load-topics/",
    views.load_topics,
    name="load_topics"
)

]
