import os

from config.dev.settings import *

WSGI_APPLICATION = 'config.prd.app.application'

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
STATIC_URL = '//assets.example.com/apps/foias/'

ALLOWED_HOSTS = [
  
  'localhost',

  'foias.example.com'

]
USE_X_FORWARDED_HOST=True

ADMINS = [('Your Name', 'your.name@example.com'), ]
SERVER_EMAIL = 'foialawya@example.com'
EMAIL_FROM_ADDRESS = os.environ.get("EMAIL_FROM_ADDRESS", 'foialawya@example.com')
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD  = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True # SSL goes with 465, TLS goes with 587, but maybe SES only supports TLS? idk.
if USE_ALLAUTH:
	# the number taken from the Site created in the prod DB.
	SITE_ID = os.environ.get("SITE_ID", 1)

DEBUG=False