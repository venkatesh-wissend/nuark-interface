from .base import *

DATABASES = {
    "nuarkDB": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "nuark_data",
        'USER': 'postgres',
        'PASSWORD': 'nivetha',
        "HOST": "localhost",
        "PORT": '5432',
    },
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nuarkDB',
        'USER': 'postgres',
        'PASSWORD': 'nivetha',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

DATABASE_ROUTERS = ["config.dbrouters.WissendRouter"]

DEBUG = True
