from django.urls import path
from .views import ClassifyUploadDataView

urlpatterns = [
    path("autoclassification", ClassifyUploadDataView.as_view(), name="job-auto-classify"),
]
