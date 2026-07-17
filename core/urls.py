from django.urls import path

from .views import AdminActivityLogView


urlpatterns = [
    path("admin-activity/", AdminActivityLogView.as_view(), name="admin-activity"),
]
