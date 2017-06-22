from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, JsonResponse
from .models import Foia, Agency, Tag, SpecialPerson

from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.contrib.auth.models import User
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings

from datetime import datetime

@receiver(pre_save, sender=User)
def prepare_user(sender, instance, **kwargs):
    if instance._state.adding is True:

        ## Don't add users not from the nytimes.com email domain.
        ## or a few whitelisted emails for testing.

        if settings.USE_ALLAUTH:
            if instance.email and settings.ALLOWABLE_LOGIN_DOMAIN and not instance.email.split('@')[1] == settings.ALLOWABLE_LOGIN_DOMAIN:
                raise Http404('Please login with your {} email address.'.format(ALLOWABLE_LOGIN_DOMAIN))

        instance.is_staff = True
        instance.is_superuser = True

# you may want to have the front-page of the site (listing all the foias)
# require you to log in to see it.
# if so, just uncomment this.
# @login_required()
def index(request):
    latest_foias = sorted(Foia.objects.order_by('-filed_date')[:50], key=lambda f: f.sort_order())
    if request.user.is_anonymous:     
        my_foias = []
    else:
        my_foias     = sorted(Foia.objects.filter(reporter=request.user), key=lambda f: f.sort_order())
    my_foias_set = set(my_foias)

    project_foias = []
    try:
        if not request.user.is_anonymous and request.user.specialperson.default_project:
            project_foias = sorted(Foia.objects.filter(tags=request.user.specialperson.default_project), key=lambda f: f.sort_order())
            project_name = request.user.specialperson.default_project.name
    except SpecialPerson.DoesNotExist:
        pass

    # for the dashboard thingy
    my_foias_count   = Foia.objects.filter(reporter=request.user).count() if not request.user.is_anonymous else 0
    all_foias_count  = Foia.objects.count()
    percent_overdue  = "TK" #Foia.objects.filter(reporter=request.user).count() / ??
    percent_complete =  int(float(Foia.objects.filter(received_response=True).filter(response_satisfactory=True).count())/all_foias_count*100) if not all_foias_count == 0 else "n/a"

    latest_foias = [item for item in latest_foias if item not in my_foias_set]
    return render(request, 'foias/index.html', 
        {'latest_foias': latest_foias, 
         'my_foias': my_foias, 
         'project_foias': project_foias,
         'warn_about_holidays': date.today()>date(2020, 11, 1),
         'my_foias_count': my_foias_count,
         'all_foias_count': all_foias_count,
         'percent_overdue': percent_overdue,
         'percent_complete': percent_complete,
        })

def project(request, tag_id):
    project_name = Tag.objects.get(id=tag_id).name
    project_foias = sorted(Foia.objects.filter(tags__id=tag_id), key=lambda f: f.sort_order())
    return render(request, 'foias/project.html', 
        {
         'project_foias': project_foias,
         'project_name': project_name,
         'warn_about_holidays': date.today()>date(2020, 11, 1),
        })


def addten(request):
    days_to_add = 10
    date_str = request.GET["date"]
    date = datetime.strptime(date_str, "%Y-%m-%d")
    f = Foia()
    new_date = f.cal.addbusdays(date, days_to_add).date()
    return JsonResponse({'old_date':date, 'new_date': new_date, 'days_added': days_to_add})

def healthcheck(request):
    return HttpResponse('', content_type="text/plain", status=200)

def all(request):
    """this page lists ALL the requests and is probably best for the lawyers or whoever"""
    result_foias = Foia.objects.all()
    paginator = Paginator(result_foias, 25)

    page = request.GET.get('page')
    try:
        result_foias = paginator.page(page)
    except PageNotAnInteger:
        result_foias = paginator.page(1)
    except EmptyPage:
        result_foias = paginator.page(paginator.num_pages)

    return render(request, 'foias/all.html', {'result_foias': result_foias})


# full text search method.
def search(request):
    query_string = request.GET['q']
    query = SearchQuery(query_string, config='simple')
    vector = SearchVector('reporter__first_name', 'reporter__last_name', 'agency__name', 
        'request_subject', 'request_notes', 'request_number',  'submission_notes', 
        'response_notes', 'response_url', 'lawsuit_notes', config='simple' )
    res = Foia.objects.annotate(rank=SearchRank(vector, query), search=vector).filter(search=query_string).order_by('-rank')[:50]
    return render(request, 'foias/search.html', {'result_foias': res, 'query': query_string })

# # this is not implemented!
# but if you wanted a page for showing details of a FOIA other than the edit page, this would be where to do it.
# you'd also have to change foias/urls.py
# def detail(request, foia_id):
#     foia = get_object_or_404(Foia, pk=foia_id)
#     return render(request, 'foias/detail.html', {'foia': foia})
