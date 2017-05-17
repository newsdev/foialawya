import os

from config.dev.settings import *

WSGI_APPLICATION = 'config.stg.app.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME', 'foialawya'),
        'USER': os.environ.get('DB_USER', 'foialawya'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'psql.example.com'),
    }
}

STATIC_ROOT = '/usr/src/app/public'
STATIC_ROOT = '/usr/src/app/public'
STATIC_URL = '//assets.example.com/apps/foias/'

ALLOWED_HOSTS = [

  'localhost',

  'foias.stg.example.com'


]


EMAIL_BACKEND =  'django.core.mail.backends.console.EmailBackend' # in staging, only sends to the log

if USE_ALLAUTH:
	# the number taken from the Site created in the prod DB.
	SITE_ID = os.environ.get("SITE_ID", 1)

DEBUG=False
