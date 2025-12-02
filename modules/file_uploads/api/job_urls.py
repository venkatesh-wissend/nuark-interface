from django.urls import path
from .views import ClassifyUploadDataView, GetJobDetailsView

urlpatterns = [
    path("autoclassification", ClassifyUploadDataView.as_view(), name="job-auto-classify"),
    path("details", GetJobDetailsView.as_view(), name="job-details"),
]
