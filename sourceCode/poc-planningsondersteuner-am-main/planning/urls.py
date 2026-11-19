from django.urls import path
from planning import views

app_name = "planning"

urlpatterns = [
    path("", views.planning_home, name="home"),
    path("beschikbaarheid/", views.availability, name="availability"),
    path("afwezigheid/", views.absence, name="absence"),
    path("weekoverzicht/", views.week_overview, name="week_overview"),
    path("vakantieaanvraag/", views.vacation_request, name="vacation_request"),
    path("vakantieaanvragen-goedkeuren/", views.approve_requests, name="approve_requests"),
    path("planner-dashboard/", views.planner_dashboard, name="planner_dashboard"),
    path(
        "planner-dashboard/export-csv/",
        views.export_weekly_planning_csv,
        name="export_weekly_planning_csv",
    ),
]
