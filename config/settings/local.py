from .base import *

DATABASES = {
    "wissendDB": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "wissendDB",
        "USER": "postgres",
        "PASSWORD": "pass",
        "HOST": "localhost",
        "PORT": '5432',
    },
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nuark_DB',
        'USER': 'postgres',
        'PASSWORD': 'pass',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

DATABASE_ROUTERS = ["config.dbrouters.WissendRouter"]

DEBUG = True
