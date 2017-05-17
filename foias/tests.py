from django.test import TestCase
from foias.models import Foia
# Create your tests here.

class EmailTestCase(TestCase):
  # tests that an email is set for each kind of date.
    # @classmethod
    # def setUpTestData(cls):
    #     # Set up data for the whole TestCase
    #     cls.foo = Foo.objects.create(bar="Test")

    # def test1(self):
    #     # Some test using self.foo
    #     ...
