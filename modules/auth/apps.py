from django.apps import AppConfig

class CustomAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.auth"
    label = "modules_auth"
