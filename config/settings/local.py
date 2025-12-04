from .base import *

DATABASES = {
    "nuarkDB": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "nuark_data",
        'USER': 'wissend',
        'PASSWORD': 'Wissend@@123',
        "HOST": "localhost",
        "PORT": '5432',
    },
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nuarkDB',
        'USER': 'wissend',
        'PASSWORD': 'Wissend@@123',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

DATABASE_ROUTERS = ["config.dbrouters.WissendRouter"]

DEBUG = True
ALLOWED_HOSTS = ['*']

# ----------------------------
# Celery Configuration
# ----------------------------
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Kolkata"  # or your local timezone
CELERY_ENABLE_UTC = True
