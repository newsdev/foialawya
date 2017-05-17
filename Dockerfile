FROM python:3.5

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uwsgi

COPY requirements.txt /usr/src/app/
RUN pip install -r /usr/src/app/requirements.txt
COPY . /usr/src/app/

ENV PYTHONPATH=/usr/src/app
ENV DJANGO_SETTINGS_MODULE=config.prd.settings
RUN django-admin collectstatic --noinput

RUN echo "daemon off;" >> /etc/nginx/nginx.conf
COPY config/prd/nginx-app.conf /etc/nginx/sites-available/default
COPY config/prd/supervisor-app.conf /etc/supervisor/conf.d/

WORKDIR /usr/src/app

EXPOSE 80
CMD ["supervisord", "-n"]
