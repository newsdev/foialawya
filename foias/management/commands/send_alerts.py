from django.core.management.base import BaseCommand, CommandError
from foias.models import Foia
from time import sleep
from datetime import datetime

class Command(BaseCommand):
    help = 'checks if any FOIAs need alerts (for due dates) and sends them. this should be run on a cron a few times a day (during the times you want to receive emails, so probably not midnight).'

    def handle(self, *args, **options):
      now = datetime.now()
      print("it's now {}, checking for emails to send.".format(now))
      if now.hour > 9 and now.hour < 17:
        for foia in Foia.objects.order_by('-filed_date'):
            foia.notify_if_necessary()
            self.stdout.write(self.style.SUCCESS('FOIA #{} is {}, {}'.format(foia.pk, foia.status(), foia.next_due_date() )))
        sleep(3600) # an hour
