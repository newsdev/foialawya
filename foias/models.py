from django.db import models
from django.core.mail import EmailMultiAlternatives
from business_calendar import Calendar
from django.contrib.auth.models import User
from django.urls import reverse
import datetime
from django.utils.safestring import mark_safe
from django.contrib.sites.models import Site
import requests
from django.conf import settings
import json

class Tag(models.Model):
  class Meta:
    verbose_name = 'Project/Tag'
    verbose_name_plural = 'Projects/Tags'  
  name = models.CharField("Tag Name", max_length=200)
  notes = models.TextField("Notes about this tag", blank=True, null=True)
  def __str__(self):
      return "{}".format(self.name)

class MyUser(User):
   class Meta:
      proxy = True
      ordering = ('first_name', 'last_name')
  
   def __str__(self):
      return self.first_name + " " + self.last_name if self.first_name and self.last_name else self.username


class SpecialPerson(models.Model):
  """a class for representing certain properties of people who aren't like other people

     like lawyers or clerks, who get notified of various steps in the FOIA process.
  """
  class Meta:
    verbose_name = 'People (Special Roles, Default Projects, etc.)'
    verbose_name_plural = 'People (Special Roles, Default Projects, etc.)'
  user = models.OneToOneField(MyUser, null=False) # many-to-one  
  is_clerk = models.BooleanField('Is this person a clerk, I mean, news assistant?', default=False)
  is_lawyer = models.BooleanField('Got a jay dee?', default=False)
  default_project = models.ForeignKey(Tag, null=True, blank=True)
  slack_handle = models.CharField("Slack Name", max_length=200, default=None, null=True)
  def __str__(self):
    if self.is_clerk and self.is_lawyer:
      return "{} is a clerk and a lawyer, which is unanticipated and probably a mistake!".format(self.user)
    elif self.is_clerk:
      return "{} is a clerk".format(self.user)
    elif self.is_lawyer:
      return "{} is a lawyer".format(self.user)
    else:
      return "{} is neither a clerk nor a lawyer.".format(self.user)

  def slack_channel(self):
    if not self.slack_handle:
      return None
    elif self.slack_handle[0] == "@":
      return self.slack_handle
    else:
      return "@{}".format(self.slack_handle)

class Agency(models.Model):
  """Represents an agency!

     Eventually, duedate stuff could be specific to agencies, e.g. noting if they don't send ack letters
     or if it's a state agency with different deadlines.
  """
  class Meta:
    verbose_name = 'Agency'
    verbose_name_plural = 'Agencies'  
    ordering = ('name',)

  name = models.CharField("Agency Name", max_length=200)
  notes = models.TextField("Notes about the agency", blank=True, null=True)
  def __str__(self):
    return self.name

class Foia(models.Model):
  class Meta:
    verbose_name = 'FOIA'
    verbose_name_plural = 'FOIAs'
    # ordering = 

  CALENDAR = 0
  BUSINESS = 1
  reporter = models.ForeignKey(MyUser, null=True,verbose_name="Who filed this request?") # many-to-one
  agency = models.ForeignKey(Agency, null=False)  

  filed_date = models.DateField('date filed')
  request_subject = models.CharField('what was the request for?', blank=True, null=True, max_length=1000)
  request_notes = models.TextField('Request text and/or notes', help_text="Did you send by mail or email? Why did you phrase it the way you did?", blank=True)
  is_state_foia = models.BooleanField("Is this a FOIA filed with a state or a foreign country?", help_text="This app doesn't know about the FOIA deadlines in those places, so you won't get notifications for these, but you're welcome to track it here.", default=False)

  received_ack_letter = models.BooleanField('Have you received an acknowledgement yet?', default=False)
  ack_date = models.DateField('date acknowledgement letter received', blank=True, null=True)
  request_number = models.CharField(max_length=200, blank=True)
  submission_notes = models.TextField('notes about the process' , blank=True, help_text="Record your phone call updates here. Did they respond by mail or email? Do you have a phone number? Did they tell you what track it\'s on?")
  date_response_due_custom = models.DateField("When are the records due? (Custom due date)", blank=True, null=True)

  received_response = models.BooleanField('Have you received responsive docs (or a denial) yet?')
  resp_date = models.DateField('date response received', blank=True, null=True)
  response_satisfactory = models.BooleanField("We're satisfied with what we got and do not need to appeal, sue or pursue this any further.", default=False)
  response_notes = models.TextField("Notes about your response.", help_text="Complain about the redactions here!", blank=True)
  response_url = models.TextField("Link to the documents and/or response letter. (Optional. Skip this if you're storing the documents on paper or offline)", blank=True, help_text="Google Drive and Dropbox are both good places to store documents and both generate shareable links you could paste here.")
  
  appealed = models.BooleanField('Have you (or your lawyer) appealed this?', default=False)
  appeal_date = models.DateField('date appeal filed', blank=True, null=True)
  lawsuit_filed = models.BooleanField('Have you (or your lawyer) filed a lawsuit over this?', default=False)
  lawsuit_filed_date = models.DateField('date lawsuit filed', blank=True, null=True)
  lawsuit_notes = models.TextField("Notes about the lawsuit ", blank=True)
  tags = models.ManyToManyField(Tag, verbose_name="What project(s) is this request a part of?", blank=True)


  # I don't want to notify people multiple times a day, ever.
  # so... this keeps track of the day of the most recent notification
  # and only sends if today is after the most recent notification date.
  last_notified = models.DateField('most recent date notified', null=True)

  # a real-life, honest-to-goodness lawyer says:
  #    The response is due 20 business days after receipt of the request (but 
  #      the agency can get a 10 business day extension if there exist "unusual circumstances").
  #    The appeal response deadline is also 20 business days after the appeal is received.
  #    The acknowledgment bit is agency by agency (it's done by regulation, generally). A lot 
  #      of them have the 10-day requirement, but I'm not sure it's true that they all do.

  ack_due_duration =             [10, BUSINESS] # 10 business days after sent (for some agencies)
  response_due_duration =        [20, BUSINESS] # 20 business days after sent (but there are extensions)
  appeal_almost_due_duration =   [85, CALENDAR] # an arbitrary Jeremy-chosen amount less than 90 days after response
  appeal_due_duration =          [90, CALENDAR] # 90 days (not business, calendar) after response
  appeal_response_due_duration = [20, BUSINESS] # 20 business days after appeal filed
  constructive_denial_duration = [90, CALENDAR] # 90 business days after acknowledgment is a constructive denail, says Derek Kravitz.

  def __str__(self):
      return "{} FOIA filed on {} by {}".format(self.agency, self.filed_date, self.reporter)

  def edit_link(self):
    return Site.objects.get_current().domain + reverse('admin:foias_foia_change', args=[self.id])


  STATUSES = {
    "LITIGATION": {
      "name": "in litigation",
      "sort_order": 10  # FOIAs in litigation are very boring (everyone who needs to know already knows)
    },
    "APPEALED": {
      "name": "appealed",
      "sort_order": 5
    },
    "RESPONSE_RECEIVED_OK": {
      "name": "response received!",
      "sort_order": 11
    },
    "RESPONSE_RECEIVED_UNAPPEALABLE": {
      "name": "response received (too late to appeal)",
      "sort_order": 6
    },
    "RESPONSE_RECEIVED_NOT_YET_APPEALED": {
      "name": "response received (not yet appealed)",
      "sort_order": 4
    },
    "ACKED": {
      "name": "acknowledged",
      "sort_order": 1
    },
    "CONSTRUCTIVELY_DENIED": {
      "name": "constructively denied?",
      "sort_order": 2
    },
    "FILED": {
      "name": "filed",
      "sort_order": 3
    },
  }

  def sort_order(self):
    """sort order for cases, based on status"""
    # apparently this is the pythonic way to do it!
    # ...
    # c'mon python.
    # these'll be sorted asc by default, so bigger numbers are at the bottom.

    return self.STATUSES[self._status()]["sort_order"]
  


  def sortable_filed_date(self):
    return self.filed_date.strftime('%s')


  def _status(self):
    if self.lawsuit_filed:
      return "LITIGATION"
    elif self.appealed:
      return "APPEALED"
    elif self.received_response: # acknowledged, responded to, but not appealed
      if self.response_satisfactory:
        return "RESPONSE_RECEIVED_OK"
      elif self.resp_date and self.date_appeal_due() < datetime.date.today():
        return "RESPONSE_RECEIVED_UNAPPEALABLE"
      else:
        return "RESPONSE_RECEIVED_NOT_YET_APPEALED"
    elif self.received_ack_letter:
      if self.constructively_denied():
        return "CONSTRUCTIVELY_DENIED"
      else:
        return "ACKED"
    else: # no lawsuit, no appeal, no response, no ack.
      return "FILED"

  def status(self):
    return self.STATUSES[self._status()]["name"]

  def is_incalculable(self):
    """For various reasons, we may not be able to know anything about certain FOIAs -- e.g. if they're filed with a state, not the feds."""
    return self.is_state_foia


  def next_due_date(self):
    if self.lawsuit_filed:
        return "ask Legal Dept."
    if self.response_satisfactory:
        return ""
    elif self.is_incalculable():
      if not self.received_response and self.date_response_due_custom:
        if self.date_response_due() < datetime.date.today():
          return "Response overdue, was due {}".format(self.date_response_due())
        else: 
          return "Agency owes us a response due {}".format(self.date_response_due())
      else:
        return "Unknown"
    else:
      if self.appealed:
        return  "Appeal response due {}".format(self.date_appeal_response_due())
      elif self.received_response: 
        if self.resp_date and self.date_appeal_due() < datetime.date.today():
          return "Too late to appeal."
        else:
          return "Appeal due {}".format(self.date_appeal_due())
      else: # not appealed and no response received yet
        if (not self.received_ack_letter) and self.date_ack_due() > datetime.date.today():
          return "Agency owes us an acknowledgement by {}".format(self.date_ack_due())
        else:
          if self.date_response_due() < datetime.date.today():
            return "Response overdue, was due {}".format(self.date_response_due())
          else: 
            return "Agency owes us a response by {}".format(self.date_response_due())

  def date_ack_due(self):
    if not self.filed_date:
      return "(not yet calculated)"
    return self._calculate_due_date(self.filed_date, *self.ack_due_duration)
  date_ack_due.short_description = 'Date acknowledgment is due (depending on agency)'

  def date_response_due(self):
    if not self.filed_date:
      return None
    if self.date_response_due_custom:
      return self.date_response_due_custom
    if self.is_incalculable():
      return None
    return self._calculate_due_date(self.filed_date, *self.response_due_duration)


  def is_overdue_notification_date(self, todays_date, number_of_days_to_remind=20, type_of_day_calculation=None):
    if type_of_day_calculation is None:
      type_of_day_calculation = self.BUSINESS
    if not self.filed_date:
      return None
    if self.is_incalculable():
      return None
    due_date =  self.date_response_due_custom if self.date_response_due_custom else self._calculate_due_date(self.filed_date, *self.response_due_duration)
    if type_of_day_calculation == self.BUSINESS:
      days_since_due_date = self.cal.busdaycount(datetime.datetime.combine(due_date, datetime.datetime.min.time()), datetime.datetime.combine(todays_date, datetime.datetime.min.time()))
    else:
      days_since_due_date = todays_date - due_date
    print(days_since_due_date)
    return days_since_due_date % number_of_days_to_remind == 0 and days_since_due_date > 0


  def date_response_due_human(self):
    return self.date_response_due() or "(not yet calculated)"
  date_response_due_human.short_description = mark_safe("When are the records due? (Automatically calculated) <a href='#' id='custom-resp-due'>Set a custom due date</a>")

  def date_appeal_almost_due(self):
    if not self.resp_date:
      return "(unknown)"
    return self._calculate_due_date(self.resp_date, *self.appeal_almost_due_duration)

  def date_appeal_due(self):
    if not self.resp_date:
      return "(90 biz days after documents are received)"
    return self._calculate_due_date(self.resp_date, *self.appeal_due_duration)
  date_appeal_due.short_description = 'Date appeal is due'

  def date_constructively_denied(self):
    if not self.ack_date:
      return None
    return self._calculate_due_date(self.ack_date, *self.constructive_denial_duration)

  def date_appeal_response_due(self):
    if not self.appeal_date:
      return "(20 days after appeal is filed)"
    return self._calculate_due_date(self.appeal_date, *self.appeal_response_due_duration)
  date_appeal_response_due.short_description = 'Date agency\'s response to appeal is due'

  def _calculate_due_date(self, from_date, day_count, day_type):
    if type(from_date) == datetime.date: # converting dates to datetimes
      from_date = datetime.datetime(*(from_date.timetuple()[:6]))
    if day_type == self.CALENDAR:
      return (from_date + datetime.timedelta(days=day_count)).date()
    elif day_type == self.BUSINESS:
      return self.cal.addbusdays( from_date, day_count).date()  
    else:
      print("UH OH THIS SHOULDN'T EVER HAPPEN LOL")
      assert False

  def constructively_denied(self):
    return self.date_constructively_denied() and self.date_constructively_denied() <= datetime.date.today()

  def check_if_ack_due(self):
    if self.is_incalculable():
      return False
    return not self.received_ack_letter and self.date_ack_due() == datetime.date.today()
  def check_if_response_due(self):
    """We might conceivably be able to know this for state/foreign FOIAs, unlike the rest."""
    return (not self.received_response) and \
            self.date_response_due() == datetime.date.today()
  def check_if_constructively_denied(self):
    return (not self.received_response) and \
            self.date_constructively_denied() == datetime.date.today()
  def check_if_appeal_almost_due(self):
    if self.is_incalculable():
      return False
    return self.received_response and self.date_appeal_almost_due() == datetime.date.today()
  def check_if_appeal_due(self):
    if self.is_incalculable():
      return False
    return self.received_response and not self.response_satisfactory and not self.appealed and self.date_appeal_due() == datetime.date.today()
  def check_if_appeal_response_due(self):
    if self.is_incalculable():
      return False
    return self.appealed and self.date_appeal_response_due() == datetime.date.today()

  def check_if_needs_reminder_about_overdueness(self, number_of_days_to_remind=20, type_of_day_calculation=None):
    if type_of_day_calculation is None:
      type_of_day_calculation = self.BUSINESS
    return (not self.received_response) and \
            self.is_overdue_notification_date(datetime.date.today(), number_of_days_to_remind, type_of_day_calculation) 

  def notify_if_necessary(self):
    # notify max once per day.
    if self.last_notified == datetime.date.today():
      return
    if self.check_if_ack_due():
      self._notify_that_ack_due()
    elif self.check_if_constructively_denied():
      self._notify_that_constructively_denied()
    elif self.check_if_response_due():
      self._notify_that_response_due()
    elif self.check_if_appeal_almost_due():
      self._notify_that_appeal_almost_due()
    elif self.check_if_appeal_due():
      self._notify_that_appeal_due()
    elif self.check_if_appeal_response_due():
      self._notify_that_appeal_response_due()
    elif self.check_if_needs_reminder_about_overdueness(20, self.BUSINESS):
      self._notify_that_response_is_overdue()
    else:
      print("checked FOIA #{}, it doesn't need any notifications".format(self.pk))
    self.last_notified = datetime.date.today()
    self.save()
  

  def _notify_that_ack_due(self):
    self._slack_notify_that_ack_due()
    self._email_notify_that_ack_due()
    self._huginn_notify_that_ack_due()
  def _notify_that_constructively_denied(self):
    self._slack_notify_that_constructively_denied()
    self._email_notify_that_constructively_denied()
    self._huginn_notify_that_constructively_denied()
  def _notify_that_response_due(self):
    self._slack_notify_that_response_due()
    self._email_notify_that_response_due()
    self._huginn_notify_that_response_due()
  def _notify_that_appeal_almost_due(self):
    self._slack_notify_that_appeal_almost_due()
    self._email_notify_that_appeal_almost_due()
    self._huginn_notify_that_appeal_almost_due()
  def _notify_that_appeal_due(self):
    self._slack_notify_that_appeal_due()
    self._email_notify_that_appeal_due()
    self._huginn_notify_that_appeal_due()
  def _notify_that_appeal_response_due(self):
    self._slack_notify_that_appeal_response_due()
    self._email_notify_that_appeal_response_due()
    self._huginn_notify_that_appeal_response_due()
  def _notify_that_response_is_overdue(self):
    self._slack_notify_that_response_is_overdue()
    self._email_notify_that_response_is_overdue()
    self._huginn_notify_that_response_is_overdue()





  def _slack_notify_that_ack_due(self):
    message = """the {} might owe you an acknowledgement on your FOIA, about '{}'.\n
It's due on {} (for some agencies). \n
if they haven't sent you one, you might want to give them a call.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.request_subject,
          self.date_ack_due(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    if settings.SLACK_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.SLACK_WEBHOOK_URL, data = json.dumps({'text': message, 'channel': self.reporter.specialperson.slack_channel(), "username": "foialawya"}))

  def _slack_notify_that_constructively_denied(self):
    message = """the {} might have constructively denied your FOIA, about '{}'.\n
It was acknowledged on {} which was 90 days ago. \n
if they haven't sent you any update, you might want to give them a call.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.request_subject,
          self.ack_date,
          self.edit_link(),
          Site.objects.get_current().domain
        )
    if settings.SLACK_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.SLACK_WEBHOOK_URL, data = json.dumps({'text': message, 'channel': self.reporter.specialperson.slack_channel(), "username": "foialawya"}))

  def _slack_notify_that_response_due(self):
    message = """the {} owes you a response, due {}, to your FOIA about '{}'. \n
If they haven't sent you a response yet, you might want to contact them.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.date_response_due(),
          self.request_subject,
          self.edit_link(),
          Site.objects.get_current().domain
          )
    if settings.SLACK_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.SLACK_WEBHOOK_URL, data = json.dumps({'text': message, 'channel': self.reporter.specialperson.slack_channel(), "username": "foialawya"}))

  def _slack_notify_that_appeal_almost_due(self):
    message = """an appeal for {}'s request from {} about '{}' is due {}. For more details, click here: {}.\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    if settings.SLACK_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.SLACK_WEBHOOK_URL, data = json.dumps({'text': message, 'channel': self.reporter.specialperson.slack_channel(), "username": "foialawya"}))

  def _slack_notify_that_appeal_due(self):
    message = """an appeal for {}'s request from {} about '{}' is due today, {}. For more details, click here: {}.\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    if settings.SLACK_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.SLACK_WEBHOOK_URL, data = json.dumps({'text': message, 'channel': self.reporter.specialperson.slack_channel(), "username": "foialawya"}))

  def _slack_notify_that_appeal_response_due(self):
    message = """an appeal for {}'s request from {} about '{}' is due back today, {}. For more details, click here: {}.\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    if settings.SLACK_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.SLACK_WEBHOOK_URL, data = json.dumps({'text': message, 'channel': self.reporter.specialperson.slack_channel(), "username": "foialawya"}))

  def _slack_notify_that_response_is_overdue(self):
    message = """the {} owes you a response, due {}, to your FOIA about '{}'. \n
If they haven't sent you a response yet, you might want to contact them.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.date_response_due(),
          self.request_subject,
          self.edit_link(),
          Site.objects.get_current().domain
          )
    if settings.SLACK_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r  = requests.post(settings.SLACK_WEBHOOK_URL, data = json.dumps({'text': message, 'channel': self.reporter.specialperson.slack_channel(), "username": "foialawya"}))

  def _huginn_notify_that_ack_due(self):
    message = """the {} might owe you an acknowledgement on your FOIA, about '{}'.\n
It's due on {} (for some agencies). \n
if they haven't sent you one, you might want to give them a call.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.request_subject,
          self.date_ack_due(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    if settings.HUGINN_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.HUGINN_WEBHOOK_URL, data = {'message': message, 'username': self.reporter.username, 'name': str(self.reporter), 'agency': self.agency, 'edit_link': self.edit_link(), 'subject': self.request_subject, 'slack_username': self.reporter.specialperson.slack_channel()})
  
  def _huginn_notify_that_constructively_denied(self):
    message = """the {} might have constructively denied your FOIA, about '{}'.\n
It was acknowledged on {} which was 90 days ago. \n
if they haven't sent you any update, you might want to give them a call.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.request_subject,
          self.ack_date,
          self.edit_link(),
          Site.objects.get_current().domain
        )
    if settings.HUGINN_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.HUGINN_WEBHOOK_URL, data = {'message': message, 'username': self.reporter.username, 'name': str(self.reporter), 'agency': self.agency, 'edit_link': self.edit_link(), 'subject': self.request_subject, 'slack_username': self.reporter.specialperson.slack_channel()})

  def _huginn_notify_that_response_due(self):
    message = """the {} owes you a response, due {}, to your FOIA about '{}'. \n
If they haven't sent you a response yet, you might want to contact them.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.date_response_due(),
          self.request_subject,
          self.edit_link(),
          Site.objects.get_current().domain
          )
    if settings.HUGINN_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.HUGINN_WEBHOOK_URL, data = {'message': message, 'username': self.reporter.username, 'name': str(self.reporter), 'agency': self.agency, 'edit_link': self.edit_link(), 'subject': self.request_subject, 'slack_username': self.reporter.specialperson.slack_channel()})
  def _huginn_notify_that_appeal_almost_due(self):
    message = """an appeal for {}'s request from {} about '{}' is due {}. For more details, click here: {}.\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    if settings.HUGINN_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.HUGINN_WEBHOOK_URL, data = {'message': message, 'username': self.reporter.username, 'name': str(self.reporter), 'agency': self.agency, 'edit_link': self.edit_link(), 'subject': self.request_subject, 'slack_username': self.reporter.specialperson.slack_channel()})
  def _huginn_notify_that_appeal_due(self):
    message = """an appeal for {}'s request from {} about '{}' is due today, {}. For more details, click here: {}.\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    if settings.HUGINN_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.HUGINN_WEBHOOK_URL, data = {'message': message, 'username': self.reporter.username, 'name': str(self.reporter), 'agency': self.agency, 'edit_link': self.edit_link(), 'subject': self.request_subject, 'slack_username': self.reporter.specialperson.slack_channel()})
  def _huginn_notify_that_appeal_response_due(self):
    message = """an appeal for {}'s request from {} about '{}' is due back today, {}. For more details, click here: {}.\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    if settings.HUGINN_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.HUGINN_WEBHOOK_URL, data = {'message': message, 'username': self.reporter.username, 'name': str(self.reporter), 'agency': self.agency, 'edit_link': self.edit_link(), 'subject': self.request_subject, 'slack_username': self.reporter.specialperson.slack_channel()})
  def _huginn_notify_that_response_is_overdue(self):
    message = """the {} owes you a response, due {}, to your FOIA about '{}'. \n
If they haven't sent you a response yet, you might want to contact them.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.date_response_due(),
          self.request_subject,
          self.edit_link(),
          Site.objects.get_current().domain
          )
    if settings.HUGINN_WEBHOOK_URL and self.reporter.specialperson and self.reporter.specialperson.slack_channel():
      r = requests.post(settings.HUGINN_WEBHOOK_URL, data = {'message': message, 'username': self.reporter.username, 'name': str(self.reporter), 'agency': self.agency, 'edit_link': self.edit_link(), 'subject': self.request_subject, 'slack_username': self.reporter.specialperson.slack_channel()})



  def _email_notify_that_ack_due(self):
    msg = EmailMultiAlternatives(
        subject='the {} might owe you an acknowledgement on your FOIA'.format(self.agency),
        body="""the {} might owe you an acknowledgement on your FOIA, about '{}'.\n
It's due on {} (for some agencies). \n
if they haven't sent you one, you might want to give them a call.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.request_subject,
          self.date_ack_due(),
          self.edit_link(),
          Site.objects.get_current().domain
        ),
        to=[self.reporter.email],
        cc=[]
        )
    html_content = """<p>the {} might owe you an acknowledgement on your FOIA, about '{}'.</p>
<p>It's due on {} (for some agencies).</p>
<p>if they haven't sent you one, you might want to give them a call.</p>
<p>if they have, please update the <a href="{}">FOIA Tracker</a><p>
<p>this message sent by the <a href="{}">FOIA Lawya app</a>.</p>
        """.format(
          self.agency, 
          self.request_subject,
          self.date_ack_due(),
          self.edit_link(),
          Site.objects.get_current().domain     
        )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)
  
  def _email_notify_that_constructively_denied(self):
    msg = EmailMultiAlternatives(
        subject='the {} might owe you an acknowledgement on your FOIA'.format(self.agency),
        body="""the {} might have constructively denied your FOIA, about '{}'.\n
It was acknowledged on {} which was 90 days ago. \n
if they haven't sent you any update, you might want to give them a call.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.request_subject,
          self.ack_date,
          self.edit_link(),
          Site.objects.get_current().domain
        ),
        to=[self.reporter.email],
        cc=[]
        )
    html_content = """<p>the {} might have constructively denied your FOIA, about '{}'.</p>
<p>It was acknowledged on {} which was 90 days ago.x.</p>
<p>if they haven't sent you one, you might want to give them a call.</p>
<p>if they have, please update the <a href="{}">FOIA Tracker</a><p>
<p>this message sent by the <a href="{}">FOIA Lawya app</a>.</p>
        """.format(
          self.agency, 
          self.request_subject,
          self.date_ack_due(),
          self.edit_link(),
          Site.objects.get_current().domain     
        )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)
  
  def _email_notify_that_response_due(self):
    msg = EmailMultiAlternatives(
        subject='the {} owes you a response to your FOIA'.format(self.agency),
        body="""the {} owes you a response, due {}, to your FOIA about '{}'. \n
If they haven't sent you a response yet, you might want to contact them.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.date_response_due(),
          self.request_subject,
          self.edit_link(),
          Site.objects.get_current().domain
          ),
        to=[self.reporter.email],
        cc=[clerk.email for clerk in User.objects.filter(specialperson__is_clerk=True)]
     )
    html_content = """<p>the {} owes you a response, due {}, to your FOIA about '{}'.</p>
<p>If they haven't sent you a response yet, you might want to contact them.
</p>
<p>if they have, please update the <a href="{}">FOIA Tracker</a><p>
<p>this message sent by the <a href="{}">FOIA Lawya app</a>.</p>
        """.format(
          self.agency, 
          self.date_response_due(),
          self.request_subject,
          self.edit_link(),
          Site.objects.get_current().domain
          )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)
  

  def _email_notify_that_appeal_almost_due(self):
    msg = EmailMultiAlternatives(
        subject="a FOIA appeal is due soon for {}'s request of {}".format(str(self.reporter), self.agency),
        body="""an appeal for {}'s request from {} about '{}' is due {}. For more details, click here: {}.\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        ),
        to=[lawyer.email for lawyer in User.objects.filter(specialperson__is_lawyer=True)],
        cc=[self.reporter.email].append([clerk.email for clerk in User.objects.filter(specialperson__is_clerk=True)])
     )
    html_content = """<p>an appeal for {}'s request from {} about '{}' is due {}. For more details, <a href="{}">visit the FOIA Tracker</a>.</p>
<p>this message sent by the <a href="{}">FOIA Lawya app</a>.</p>
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)
  

  def _email_notify_that_appeal_due(self):
    msg = EmailMultiAlternatives(
        subject="a FOIA appeal is due today for {}'s request of {}".format(str(self.reporter), self.agency),
        body="""an appeal for {}'s request from {} about '{}' is due today, {}. For more details, click here: {}.\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        ),
        to=[lawyer.email for lawyer in User.objects.filter(specialperson__is_lawyer=True)],
        cc=[self.reporter.email] + [clerk.email for clerk in User.objects.filter(specialperson__is_clerk=True)]
     )
    html_content = """<p>an appeal for {}'s request from {} about '{}' is due today, {}. For more details, click here: <a href="{}">visit the FOIA Tracker</a>.</p>
<p>this message sent by the <a href="{}">FOIA Lawya app</a>.</p>
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)
  

  def _email_notify_that_appeal_response_due(self):
    msg = EmailMultiAlternatives(
        subject="a FOIA response is due back today for {}'s request of {}".format(str(self.reporter), self.agency),
        body="""an appeal for {}'s request from {} about '{}' is due back today, {}. For more details, click here: {}.\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        ),
        to=[lawyer.email for lawyer in User.objects.filter(specialperson__is_lawyer=True)],
        cc=[self.reporter.email] + [clerk.email for clerk in User.objects.filter(specialperson__is_clerk=True)]
     )
    html_content = """<p>an appeal for {}'s request from {} about '{}' is due back today, {}. For more details, click here: <a href="{}">visit the FOIA Tracker</a>.</p>
<p>this message sent by the <a href="{}">FOIA Lawya app</a>.</p>
        """.format(
          str(self.reporter), 
          self.agency, 
          self.request_subject,
          self.appeal_almost_due_date(),
          self.edit_link(),
          Site.objects.get_current().domain
        )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)


  def _email_notify_that_response_is_overdue(self):
    msg = EmailMultiAlternatives(
        subject='the {}\'s response to your FOIA is overdue'.format(self.agency),
        body="""the {} owes you a response, due {}, to your FOIA about '{}'. \n
If they haven't sent you a response yet, you might want to contact them.\n
if they have, please update the FOIA Tracker: {}\n
this message sent by the FOIA Lawya app ({}).
        """.format(
          self.agency, 
          self.date_response_due(),
          self.request_subject,
          self.edit_link(),
          Site.objects.get_current().domain
          ),
        to=[self.reporter.email],
        cc=[clerk.email for clerk in User.objects.filter(specialperson__is_clerk=True)]
     )
    html_content = """<p>the {} owes you a response, due {}, to your FOIA about '{}'.</p>
<p>If they haven't sent you a response yet, you might want to contact them.
</p>
<p>if they have, please update the <a href="{}">FOIA Tracker</a><p>
<p>this message sent by the <a href="{}">FOIA Lawya app</a>.</p>
        """.format(
          self.agency, 
          self.date_response_due(),
          self.request_subject,
          self.edit_link(),
          Site.objects.get_current().domain
          )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)
  

  holidays =[
     # https://www.opm.gov/policy-data-oversight/snow-dismissal-procedures/federal-holidays/#url=2017
    "2020-1-1",    # Wednesday,    #  New Year's Day
    "2020-1-20",    # Monday,      #  Birthday of Martin Luther King, Jr.
    "2020-2-17",    # Monday,      #  Washington's Birthday
    "2020-5-25",    # Monday,      #  Memorial Day
    "2020-7-3",    # Friday,       #  Independence Day
    "2020-9-7",    # Monday,       #  Labor Day
    "2020-10-12",    # Monday,     #  Columbus Day
    "2020-11-11",    # Wednesday,  #  Veterans Day
    "2020-11-26",    # Thursday,   #  Thanksgiving Day
    "2020-12-25",    # Friday,     #  Christmas Day


    "2019-1-1",    # Tuesday,             #  New Year's Day
    "2019-1-21",    # Monday,       #  Birthday of Martin Luther King, Jr.
    "2019-2-18",    # Monday,       #*  Washington's Birthday
    "2019-5-27",    # Monday,       #  Memorial Day
    "2019-7-4",    # Thursday,             #  Independence Day
    "2019-9-2",    # Monday,       #   Labor Day
    "2019-10-14",    # Monday,       #  Columbus Day
    "2019-11-11",    # Monday,       #   Veterans Day
    "2019-11-28",    # Thursday,             #   Thanksgiving Day
    "2019-12-25",    # Wednesday,             #  Christmas Day


    "2018-1-1",    # Monday,      #   New Year's Day
    "2018-1-15",    # Monday,      #  Birthday of Martin Luther King, Jr.
    "2018-2-19",    # Monday,      #*  Washington's Birthday
    "2018-5-28",    # Monday,      #  Memorial Day
    "2018-7-4",    # Wednesday,            #   Independence Day
    "2018-9-3",    # Monday,      #   Labor Day
    "2018-10-8",    # Monday,      #   Columbus Day
    "2018-11-12",    # Monday,      #**   Veterans Day
    "2018-11-22",    # Thursday,            #   Thanksgiving Day
    "2018-12-25",    # Tuesday,            #  Christmas Day


    "2017-1-2",    # Monday,      #*  New Year's Day
    "2017-1-16",    # Monday,      #  Birthday of Martin Luther King, Jr.
    "2017-2-20",    # Monday,      #**   Washington's Birthday
    "2017-5-29",    # Monday,      #  Memorial Day
    "2017-7-4",    # Tuesday,      #   Independence Day
    "2017-9-4",    # Monday,      #   Labor Day
    "2017-10-9",    # Monday,      #   Columbus Day
    "2017-11-10",    # Friday,      #***  Veterans Day
    "2017-11-23",    # Thursday,      #   Thanksgiving Day
    "2017-12-25",    # Monday,      #   Christmas Day
  ]
  cal = Calendar(holidays=holidays)


