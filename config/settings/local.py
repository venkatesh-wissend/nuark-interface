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
