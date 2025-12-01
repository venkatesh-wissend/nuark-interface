from .base import *

DATABASES = {
    "nuarkDB": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "nuark_db", # Secondary DB 
        "USER": "postgres",
        "PASSWORD": "pass",
        "HOST": "localhost",
        "PORT": '5432',
    },
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nuark_DB', # DB in local (Default DB)
        'USER': 'postgres',
        'PASSWORD': 'pass',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

DATABASE_ROUTERS = ["config.dbrouters.WissendRouter"]

DEBUG = True
