from django.urls import path
from .views import UploadFileView

urlpatterns = [
    path("file", UploadFileView.as_view()),
    # path("classify", ClassifyUploadDataView.as_view(), name="classify-upload"),
]
