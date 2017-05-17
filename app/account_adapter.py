from django.conf import settings

if settings.USE_ALLAUTH:

  from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
  from allauth.socialaccount import app_settings
  from allauth.account.utils import user_email, user_field, user_username
  from foias.models import User
  from allauth.account.adapter import get_adapter as get_account_adapter

  class SocialAccountAdapter(DefaultSocialAccountAdapter):
      def save_user(self, request, new_social_login, form, commit=False):
        """if a user who has an account already created logs in, merge the two accounts 
          
           (rather than complaining about duplicate email addresses)
        """
          # cf:
          # https://github.com/pennersr/django-allauth/blob/0367b51514e592db011511e420570789c7d1df75/allauth/socialaccount/models.py#L158
          # https://github.com/pennersr/django-allauth/blob/0367b51514e592db011511e420570789c7d1df75/allauth/socialaccount/adapter.py#L70

          serialized = new_social_login.serialize()

          new_user_email = serialized['email_addresses'][0]['email']
          # if there's another user with this same email address 
          # (that's unpaired with the Google Account)... 
          # delete the new one and merge it's social account with the old one.
          already_existing_user = User.objects.all().filter(email=new_user_email).first()
          if already_existing_user and not already_existing_user.socialaccount_set.count():
            new_social_login.connect(user=already_existing_user, request=request)
            already_existing_user.first_name = new_social_login.account.extra_data['given_name']
            already_existing_user.last_name = new_social_login.account.extra_data['family_name']
            already_existing_user.save()
          else:
            new_user = new_social_login.user
            new_user.set_unusable_password()
            if form:
                get_account_adapter().save_user(request, new_user, form)
            else:
                get_account_adapter().populate_username(request, new_user)
            new_social_login.save(request)
          return new_social_login.user

      def is_auto_signup_allowed(self, request, sociallogin):
          # If email is specified, check for duplicate and if so, no auto signup.
          auto_signup = app_settings.AUTO_SIGNUP
          if auto_signup:
              email = user_email(sociallogin.user)
              # Let's check if auto_signup is really possible...
              if not email and app_settings.EMAIL_REQUIRED:
                  # Nope, email is required and we don't have it yet...
                  auto_signup = False
          return auto_signup
