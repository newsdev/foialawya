"""foialawya URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin

from foias import views


from django.conf import settings

if settings.USE_ALLAUTH:
    from django.contrib.auth.decorators import login_required
    from django.contrib.auth.views import logout

    admin.site.login = login_required(admin.site.login)

admin.site.site_title = 'FOIAs'
admin.site.site_header = 'FOIAs'
admin.site.index_title = 'Track your FOIAs'


urlpatterns = [
    url(r'^foias/', include('foias.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^$', views.index, name='index'),
  ]

if settings.USE_ALLAUTH:
    urlpatterns += [
        url(r'^foias/accounts/logout/$', logout, {'next_page': '/foias/admin/'}),
        url(r'^foias/accounts/', include('allauth.urls')),  
    ]