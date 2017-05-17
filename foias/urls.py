from django.conf.urls import url

from . import views
app_name = 'foias'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^healthcheck$', views.healthcheck, name="healthcheck"),
    url(r'^search$', views.search, name="search"),
    url(r'^all$', views.all, name="all"),    


    # # this is not implemented!
	# but if you wanted a page for showing details of a FOIA other than the edit page, you'd have to uncomment this
	# and make some changes in /foias/views.py
    # ex: /foias/5/
    # url(r'^(?P<foia_id>[0-9]+)/$', views.detail, name='detail'),    
]
