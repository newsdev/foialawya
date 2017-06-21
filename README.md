Foia Lawya
==========

Yelling "FOIA" in a Crowded Newsroom
------------------------------------

This app keeps track of FOIAs filed by the various investigative teams -- or any reporter, tbh -- to avoid duplication and alert reporters, editors and lawyers of impending deadlines.

### The app has three main capabilities:

- lets a reporter or editor see what FOIAs their colleagues have filed (to avoid duplicate work)
- lets a reporter or a clerk add details of a FOIA they just filed, in order to get email notifications when due dates occur.
- lets lawyers get a birds-eye view of FOIAs that our reporters have filed.

#### When reporters will get an email

- 10 business days after filing, if the agency hasn't yet acknowledged your request.
- 20 business days after filing, if the agency hasn't sent you docs yet or sent a revised due date.
- 85 and 90 business days after you receive a response, to remind you to appeal if necessary.
- 20 business days after an appeal is filed, when the response to the appeal is due.

#### When clerks will be cc'ed on an email

- 20 business days after filing, if the agency hasn't sent the reporter their docs yet or sent a revised due date.
- 85 and 90 business days after you receive a response, to remind you to appeal if necessary. 

#### When lawyers will get an email

- 85 and 90 business days after you receive a response, to remind you to appeal if necessary.
- 20 business days after an appeal is filed, when the response to the appeal is due.

Should I just put this on the internet?
---------------------------------------

No. Please, no. FOIA Lawya is built with an assumption of trust -- that your colleagues aren't going to intentionally try to mess with your stuff. You'd have to create a whole new permissions model if you wanted to put this on the public internet somewhere.

Deployment
==========

This is a plain-jane Django app. Deploy it however you'd deploy a Django app. We use Docker + Kubernetes, using the included Docker image, which does everything you need.

Configuration is mostly done by environment variables -- for your database details and for a server from which to send emails: 

- `DB_HOST`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `EMAIL_HOST`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_HOST_USER`
- `EMAIL_PORT`

You also need to do this for the link to your site to work in emails: 

1. Add the domain of your site here: http://wherever.its.deployed.example.com/admin/sites/site/
2. Once you do, take the number from the URL (the `2` from `http://wherever.its.deployed.example.com/admin/sites/site/2/change/`) and then set the SITE_ID variable to it. (e.g. `SITE_ID=2`)

Slack integration
-----------------

FOIA Lawya can send notifications via Slack along with email (or instead of it).  FOIA Lawya will alert users via a private Slackbot message. 
 There are two steps to setting this up:
 - add the `SLACK_WEBHOOK_URL` environment variable and set it to your Slack webhook URL.
 - also, set the Slack handle for each user who wants Slack notifications in the SpecialPerson portion of the admin. (Users without slack handles won't get notifications.)

Huginn integration
------------------

If you'd like alerts sent to Huginn (kind of like IFTTT or Yahoo Pipes), so you can dispatch them somewhere else, use the `HUGINN_WEBHOOK_URL`.

Docker Compose (How to run FOIA Lawya locally)
----------------------------------------------

Just run `docker-compose up` in this directory, then visit [localhost:8080](http://localhost:8080) in your browser. You'll need to have [Docker Compose](https://docs.docker.com/compose/install/) installed first.

You'll see a demo version of FOIA Lawya. It doesn't send alerts -- unless you were to modify the docker-compose file to set the email-related environment variables above -- so it's not really going to be super useful to you unless you deploy it for real. To b clear, the version you get this way is probably best for testing out FOIA Lawya, not for using it for real.

Authentication
--------------

The open-source version of FOIA Lawya uses the default Django Admin system. 

The pre-created user has the username `superuser` and the password `password`. If you're using this for real, you should [delete this user](http://localhost:8080/admin/auth/user/1/change/) after you create a real one for yourself.

However, our internal version uses django-allauth, which is included here. If you want to turn it on, follow these directions.

The benefits of the OAuth system is that it allows your users to "seamlessly" log in. They don't have to create a new username/password for FOIA Lawya, but can instead use their main Google account. 

1. Add the domain of your site here: http://localhost:8080/admin/sites/site/
2. Once you do, take the number from the URL (the `2` from `http://whatever.com/admin/sites/site/2/change/`) and then set the SITE_ID variable to it. (e.g. `SITE_ID=2`)
3. Now, set the ALL_AUTH environment variable to `True` (or `1`)
4. Visit http://localhost:8080/admin/.
5. You should see, under the SOCIAL ACCOUNTS header, a link to Social Applications. Click it.
6. Set up a new Social Application by obtaining a client ID and secret key from the OAuth provider -- probably Google. Enter those into the form. Name it whatever you want.
7. IMPORTANT: select your site's name (that you set up in step #1) on the right-hand side under "Available Sites" and click to move it to the "Chosen Sites" pane. Then hit save.
8. You should now be able to open an Incognito/Private Browsing window and log in to your site with Google.

That should be about it. Open an issue if you run into any hiccups.

To Run Locally, not with Docker Compose
---------------------------------------
```
pip install -r requirements.txt 
createdb foialawya
python manage.py migrate
python manage.py loaddata foias/fixtures/opensource.yaml
python manage.py runserver
```

Design philosophy and thoughts
==============================

I wrote about how to data-model FOIAs here: https://source.opennews.org/articles/foia-data-models/

Eventually (TODO):
==================
- State rules/deadlines.

Notes on things that'll eventually cause problems:
==================================================

There is not currently a full-text index (as of 3/28/17) but it might eventually be necessary. And if so, it wouldn't be reflected in code here (Django: ¯\\\_(ツ)\_/¯).

