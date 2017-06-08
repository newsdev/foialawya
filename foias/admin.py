from django.contrib import admin
from .models import Foia, SpecialPerson, Agency
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.forms.models import model_to_dict

from django import template

register = template.Library()


@admin.register(Foia)
class FoiaAdmin(admin.ModelAdmin):
    class Media: # oh, because this makes sense. yeah, just add a magically-named class inside your class.
        js = ('//code.jquery.com/jquery-2.1.4.min.js',)
        # css = {
        #      'all': ('css/admin/my_own_admin.css',)
        # }    
    readonly_fields = ('date_ack_due', 'date_appeal_due', 'date_response_due_human')
    # list_display = ()
    fieldsets = [
        ('1. Did you just file a FOIA?', {'fields': [
            'reporter',
            'filed_date',
            'agency',
            'is_state_foia',
            'request_subject',
            'request_notes',

            'tags'

        ],
        'description': """Once you enter the details of your FOIA here, this app will calculate the due dates and send you email alerts if the agency blows its deadline for responding.<br/>
        <br />
        If you filed the same FOIA with two agencies, please fill out this form once for each one.
        """
        }),
        ('2. Did the agency just acknowledge your FOIA?', {'fields': [
            'date_ack_due',
            'received_ack_letter',
            'ack_date',
            'request_number',
            'submission_notes',
            'date_response_due_human',
            'date_response_due_custom',            
        ],
        'description': ""
        }),
        ('3. Did the agency just respond to your FOIA?', {'fields': [
            'received_response',
            'resp_date',
            'response_satisfactory',
            'response_notes',
            'response_url',
            'date_appeal_due'
        ],
        'description': ""
        }),
        ("4. Did we just appeal your FOIA's denial/redactions?", {'fields': [
            'appealed',
            'appeal_date',
            # 'date_appeal_response_due'
        ],
        'description': ""
        }),
        ("5. Are we suing over your FOIA's denial/redactions?", {'fields': [
            'lawsuit_filed',
            'lawsuit_filed_date',
            'lawsuit_notes'
        ],
        'description': ""
        }),
    ]

    def duplicate_without_agency(self, request, foia):
        ret = super(FoiaAdmin, self).response_change(request, foia)
        foia.save()

        # I don't know what all this does. 
        # We're just going to the create page, but with the ?duplicatefoia param set to the pk of the FOIA we want to duplicate.
        # the rest of the work is in get_changeform_initial_data
        preserved_filters = self.get_preserved_filters(request)
        opts = foia._meta        
        redirect_url = reverse('admin:foias_foia_add',
                           current_app=self.admin_site.name)
        redirect_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, redirect_url)
        return HttpResponseRedirect(redirect_url + "?duplicatefoia={}".format(foia.pk))
        # http://whatever/admin/foias/foia/add/

    def response_add(self, request, foia, post_url_continue=None):
        if "_duplicate" in request.POST:
            ret = super(FoiaAdmin, self).response_change(request, foia)
            foia.save()            
            return self.duplicate_without_agency(request, foia);            
        else:
            ret = super(FoiaAdmin, self).response_add(request, foia, post_url_continue=None)
            foia.save()
            # `return ret` would send you to the Foia list under admin.
            return HttpResponseRedirect('/')

    def response_change(self, request, foia):
        if "_duplicate" in request.POST:
            ret = super(FoiaAdmin, self).response_change(request, foia)
            foia.save()            
            return self.duplicate_without_agency(request, foia);
        else:
            ret = super(FoiaAdmin, self).response_change(request, foia)
            foia.save()
            # `return ret` would send you to the Foia list under admin.
            return HttpResponseRedirect('/')


    # this is the 
    def get_changeform_initial_data(self, request):
        """Sets the initial state of the Create FOIA form"""
        initial_data = super(FoiaAdmin, self).get_changeform_initial_data(request)
        initial_data['reporter'] = request.user.pk
        try:
            if request.user.specialperson.default_project:
                initial_data['tags'] = [request.user.specialperson.default_project]
        except SpecialPerson.DoesNotExist:
            pass

        if 'duplicatefoia' in request.GET:
            id_of_foia_to_dupe = request.GET['duplicatefoia']
            foia_to_dupe = model_to_dict(Foia.objects.get(pk=id_of_foia_to_dupe))
            attributes_to_dupe = {
                'filed_date': foia_to_dupe['filed_date'],
                'is_state_foia': foia_to_dupe['is_state_foia'],
                'request_subject': foia_to_dupe['request_subject'],
                'request_notes': foia_to_dupe['request_notes']
            }
            initial_data.update(attributes_to_dupe) 
            # nothing is done with this right now.
            # eventually I'd like to keep track of this.
            initial_data["duplicate_of"] = id_of_foia_to_dupe 
        return initial_data

    def response_delete(self, request, obj_display, obj_id):
        return redirect('/')

    @register.inclusion_tag('admin/submit_line.html', takes_context=True)
    def custom_submit_row(context):
        """
        Displays the row of buttons for delete and save.
        """
        opts = context['opts']
        change = context['change']
        is_popup = context['is_popup']
        save_as = context['save_as']
        ctx = {
            'opts': opts,
            'show_delete_link': (
                not is_popup and context['has_delete_permission'] and
                change and context.get('show_delete', True)
            ),
            'show_save_as_new': not is_popup and change and save_as,
            'show_save_and_add_another': (
                context['has_add_permission'] and not is_popup and
                (not save_as or context['add'])
            ),
            'show_save_and_continue': not is_popup and context['has_change_permission'],
            'is_popup': is_popup,
            'show_save': True,
            'preserved_filters': context.get('preserved_filters'),
        }
        if context.get('original') is not None:
            ctx['original'] = context['original']
        return ctx


@admin.register(SpecialPerson)
class SpecialPersonAdmin(admin.ModelAdmin):
    fields = ["is_clerk", "is_lawyer", "user", "default_project"]

@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    pass

