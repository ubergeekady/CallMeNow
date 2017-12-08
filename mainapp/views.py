from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings as django_settings
from django.core.mail import send_mail
from django.template.loader import get_template
from django.core.urlresolvers import reverse
from django.db.models import Count, Case, When, IntegerField

from .models import Signups, Accounts, UserProfile, \
    Widget,Plans,Subscriptions, ForgotPassword, WidgetAgent, Leads, CallQueue, Calls, Notes, Countries

import urllib
import random
import datetime
import pytz
import uuid
import json
import requests

import plivo
import rollbar
from plivo import plivoxml
from postmarker.core import PostmarkClient
from geolite2 import geolite2
from pyisemail import is_email


def index(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        email = request.POST['email'].lower()
        email = email.lstrip().rstrip()
        if not is_email(email):
            return render(request, 'mainapp/0login.html', {'error': 'Invalid Email Address', 'request' : request.POST})

        password = request.POST['password']
        user = authenticate(username=email, password=password)
        if user==None:
            return render(request, 'mainapp/0login.html', {'error':'Unable to authenticate', 'request' : request.POST})
        else:
            login(request, user)
            return HttpResponseRedirect(reverse('mainapp:home'))

    else:
        return render(request, 'mainapp/0login.html')

def sign_up(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        name = request.POST.get('name', "")
        phone = request.POST.get('phone', "")
        email = request.POST.get('email', "").lower()
        pass1 =  request.POST.get('pass1', "")
        pass2 = request.POST.get('pass2', "")
        if not is_email(email):
            return render(request, 'mainapp/0signup.html', {'error': 'Invalid Email Address', 'request' : request.POST})
        if pass1 != pass2:
            return render(request, 'mainapp/0signup.html', {'error': 'Passwords do not match', 'request' : request.POST})
        if len(pass1)<8:
            return render(request, 'mainapp/0signup.html', {'error': 'Please enter a password of atleast 8 characters', 'request' : request.POST})
        if User.objects.filter(email=email).exists():
            return render(request, 'mainapp/0signup.html', {'error': "User with this email address already exists", 'request' : request.POST})
        if not is_phone(phone):
            return render(request, 'mainapp/0signup.html', {'error': 'Invalid phone number', 'request' : request.POST})
        if UserProfile.objects.filter(phone=phone).exists():
            return render(request, 'mainapp/0signup.html', {'error': 'User with this phone number already exists', 'request': request.POST})

        if phone[0] == "+":
            phone = phone.lstrip("+")
        email = email.lstrip().rstrip()

        uid = uuid.uuid4().hex[:20]
        a = Signups(uuid=uid, name=name, email=email, phone=phone, password=pass1)
        a.save()
        link = "https://"+django_settings.HOME_URL+"/emailconfirm/" + uid + "/"
        template = get_template('emails/email_signup.html')
        html_content = template.render({"confirmlink":link})
        subject = "Please validate your email address."
        callmenow_email(subject, html_content, email)

        template = get_template('emails/admin_newsignup.html')
        html_content = template.render({"homeurl":django_settings.HOME_URL, "name":name, "email":email, "phone":phone})
        subject = "New Signup At CallMeNow"
        callmenow_email(subject, html_content, "aditya@impulsemedia.co.in")

        print(link)
        return render(request, 'mainapp/0signup.html', {'success':True})
    else:
        return render(request, 'mainapp/0signup.html')

def email_confirm(request, uuid):
    signupobj= get_object_or_404(Signups, uuid=uuid)
    User.objects.create_user(signupobj.email, signupobj.email, signupobj.password)
    user = authenticate(username=signupobj.email, password=signupobj.password)

    reader = geolite2.reader()
    country = reader.get(get_client_ip(request))
    try:
        if country["location"]["time_zone"] in pytz.common_timezones:
            tzone=country["location"]["time_zone"]
        else:
            tzone="UTC"
    except:
        tzone="UTC"

    #Signup at FirstPromoter
    post_data = {'api_key': django_settings.FIRSTPROMOTER_APIKEY, 'email': signupobj.email, 'first_name': signupobj.name}
    response = requests.post('https://firstpromoter.com/api/v1/promoters/create', data=post_data)
    content = json.loads(response.content)
    try:
        firstpromoter_token = content['auth_token']
    except:
        firstpromoter_token = ""

    ac = Accounts.objects.create(owner=user, timezone=tzone, firstpromoter_authid=firstpromoter_token)
    UserProfile.objects.create(user=user, account=ac, name=signupobj.name, usertype='Owner', phone=signupobj.phone)
    signupobj.delete()
    login(request, user)
    return render(request, 'mainapp/0signup_emailverify.html')

def logoutpage(request):
    logout(request)
    return HttpResponseRedirect(reverse('mainapp:index'))

def forgotpassword(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        email = request.POST['email'].lower()
        user = get_object_or_404(User, email=email)
        uid = uuid.uuid4().hex[:20]
        a = ForgotPassword(uuid=uid, user=user)
        a.save()
        link = "https://"+django_settings.HOME_URL+"/forgot_password_confirm/" + uid + "/"
        template = get_template('emails/email_forgotpassword.html')
        html_content = template.render({"confirmlink":link})
        subject = "Password reset link"
        callmenow_email(subject, html_content, email)
        print(link)
        return render(request, 'mainapp/0forgot_password.html', {'message':'Please check your email and click on the validation link. If you do not recieve the email, please contact support@callmenowhq.com'})
    else:
        return render(request, 'mainapp/0forgot_password.html')

def forgot_password_confirm(request, uuid):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        uuid=request.POST['uuid']
        passobj = get_object_or_404(ForgotPassword, uuid=uuid)
        pass1=request.POST['pass1']
        pass2=request.POST['pass2']
        if pass1 != pass2:
            return render(request, 'mainapp/0forgot_password_confirm.html', {'uuid': uuid , "error":"Passwords do not match"})
        else:
            passobj.user.set_password(pass1)
            passobj.user.save()
            passobj.delete()
            return render(request, 'mainapp/0forgot_password_confirm.html', {'uuid': uuid, "success": "Password changed."})
    else:
        passobj= get_object_or_404(ForgotPassword, uuid=uuid)
        return render(request, 'mainapp/0forgot_password_confirm.html', {'uuid':uuid})


@login_required
def changepassword(request):
    if request.method == 'POST':
        pass1=request.POST['pass1']
        pass2=request.POST['pass2']
        if pass1 != pass2:
            return render(request, 'mainapp/changepassword.html', {"error":"Passwords do not match"})
        if len(pass1)<8:
            return render(request, 'mainapp/changepassword.html', {"error":"Password should be minimum 8 characters long"})

        request.user.set_password(pass1)
        request.user.save()
        return render(request, 'mainapp/changepassword.html', {"success": "Password changed"})

    else:
        return render(request, 'mainapp/changepassword.html')

@login_required
def gettingstarted(request):
    session_usertype = request.user.userprofile.usertype
    session_account = request.user.userprofile.account
    if session_usertype == "Agent" or session_usertype == "Admin":
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.user.userprofile.account.onboarded == True:
        return HttpResponseRedirect(reverse('mainapp:home'))

    w = Widget.objects.create(account=session_account, name="Widget #1",
                          greeting_text="Please wait while we transfer your call",
                          call_setting="AgentFirst",
                          allowed_countries=[],
                          call_algorithm="Simultaneous",
                          capture_leads=True,
                          show_on_mobile=True)
    w.save()
    a = WidgetAgent(widget=w, user=request.user.userprofile)
    a.save()
    print(w.id)
    request.user.userprofile.account.onboarded = True
    request.user.userprofile.account.save()
    return render(request, 'mainapp/gettingstarted.html', {"widgetId" : w.id})


@login_required
def home(request):
    session_usertype = request.user.userprofile.usertype
    session_account = request.user.userprofile.account
    context={}

    nowobject = datetime.datetime.now(pytz.timezone(session_account.timezone))

    today = nowobject.date()
    aggregate_calls = Calls.objects.filter(datetime__contains=today, account=session_account).values('callmenow_status').annotate( dcount=Count('callmenow_status'))

    for a in aggregate_calls:
        if a['callmenow_status']=="call-completed":
            context['today_calls_completed'] = a['dcount']
        if a['callmenow_status']=="call-failed":
            context['today_calls_failed'] = a['dcount']

    if "today_calls_failed" not in context:
        context['today_calls_failed']=0
    if "today_calls_completed" not in context:
        context['today_calls_completed']=0

    context['today_total_calls'] = context['today_calls_failed'] + context['today_calls_completed']

    context["today_new_leads"] = Leads.objects.filter(datetime__contains=today, account=session_account).count()
    context["chart_items"] = Calls.objects.filter(account=session_account, datetime__lte=nowobject,datetime__gt=nowobject + datetime.timedelta(days=-30)).extra({'date': 'date(datetime)'}).values('date').annotate(call_failed=Count(Case(When(callmenow_status="call-failed", then=1),output_field=IntegerField())) , call_completed=Count(Case(When(callmenow_status="call-completed", then=1),output_field=IntegerField())))

    if len(context["chart_items"])==0:
        context['chart_items']= [{'date':'Today', 'call_failed':0, 'call_completed':0}]

    return render(request, 'mainapp/home.html', context)

@login_required
def team(request):
    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    session_accountId = request.user.userprofile.account.id
    session_account = request.user.userprofile.account

    team = UserProfile.objects.filter(account=session_account)
    for t in team:
        w = []
        widgetagents = WidgetAgent.objects.filter(user = t)
        for widgetagent in widgetagents:
            w.append(widgetagent.widget.name)
        t.widgets = ", ".join(w)
    return render(request, 'mainapp/team.html', {'team':team})

@login_required
def toggleavailability(request, user_id, value):
    userobj = get_object_or_404(UserProfile, id=user_id)
    if value=="true":
        userobj.available=True
    else:
        userobj.available=False
    userobj.save()
    success={'success':True}
    return HttpResponse(json.dumps(success))

@login_required
def team_create_new(request):
    session_usertype = request.user.userprofile.usertype
    session_accountId = request.user.userprofile.account.id
    session_account = request.user.userprofile.account

    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        name = request.POST.get('name', "")
        phone = request.POST.get('phone', "")
        email = request.POST.get('email', "").lower()
        email = email.lstrip().rstrip()
        availability_hours = request.POST.get('availability_hours', "9,18").split(",")
        usertype = request.POST.get('usertype', "")

        if len(name)<2:
            return render(request, 'mainapp/create_new_user.html', {'error': 'Please enter a name longer than 2 characters', 'request': request.POST})
        if not is_phone(phone):
            return render(request, 'mainapp/create_new_user.html', {'error': 'Please enter a valid phone number', 'request': request.POST})
        if not is_email(email):
            return render(request, 'mainapp/create_new_user.html', {'error': 'Please enter a valid email address', 'request': request.POST})
        if usertype not in ["Admin","Agent"]:
            return render(request, 'mainapp/create_new_user.html', {'error': 'Please select a user type', 'request': request.POST})
        if User.objects.filter(email=email).exists():
            return render(request, 'mainapp/create_new_user.html', {'error': 'User with this email Id already exists', 'request':request.POST})
        if UserProfile.objects.filter(phone=phone).exists():
            return render(request, 'mainapp/create_new_user.html', {'error': 'User with this phone number already exists', 'request': request.POST})

        sms_missed_calls = False if request.POST.get('sms_missed_calls')==None else True
        sms_completed_calls  = False if request.POST.get('sms_completed_calls')==None else True
        sms_new_lead  = False if request.POST.get('sms_new_lead')==None else True
        email_missed_calls = False if request.POST.get('email_missed_calls')==None else True
        email_completed_calls = False if request.POST.get('email_completed_calls')==None else True
        email_new_lead = False if request.POST.get('email_new_lead')==None else True
        email_widget_daily_reports = False if request.POST.get('email_widget_daily_reports')==None else True
        email_widget_weekly_reports = False if request.POST.get('email_widget_weekly_reports')==None else True
        monday = False if request.POST.get('monday') == None else True
        tuesday = False if request.POST.get('tuesday') == None else True
        wednesday = False if request.POST.get('wednesday') == None else True
        thursday = False if request.POST.get('thursday') == None else True
        friday = False if request.POST.get('friday') == None else True
        saturday = False if request.POST.get('saturday') == None else True
        sunday = False if request.POST.get('sunday') == None else True

        if phone[0] == "+":
            phone = phone.lstrip("+")

        user = User.objects.create_user(email, email, 'testpass')
        UserProfile.objects.create(user=user, account=session_account, name=name, usertype=usertype,
            phone=phone, sms_missed_calls = sms_missed_calls,
            sms_completed_calls = sms_completed_calls,
            sms_new_lead = sms_new_lead,
            email_missed_calls = email_missed_calls,
            email_completed_calls = email_completed_calls,
            email_new_lead = email_new_lead,
            email_widget_daily_reports = email_widget_daily_reports,
            email_widget_weekly_reports = email_widget_weekly_reports,
            available_from = int(availability_hours[0]),
            available_to=int(availability_hours[1]),
            monday = monday,
            tuesday=tuesday,
            wednesday=wednesday,
            thursday=thursday,
            friday=friday,
            saturday=saturday,
            sunday=sunday
        )
        uid = uuid.uuid4().hex[:20]
        a = ForgotPassword(uuid=uid, user=user)
        a.save()
        link = "https://"+django_settings.HOME_URL+"/passwordchange/" + uid + "/"
        print(link)
        template = get_template('emails/email_agentinvite.html')
        html_content = template.render({"confirmlink":link})
        subject = "You have been invited to join CallMeNow"
        callmenow_email(subject, html_content, email)
        return HttpResponseRedirect(reverse('mainapp:team'))
    else:
        return render(request, 'mainapp/create_new_user.html')


@login_required
def team_edit(request,user_id):
    userobj = get_object_or_404(UserProfile, id = user_id)
    session_usertype = request.user.userprofile.usertype
    session_accountId = request.user.userprofile.account.id

    if userobj.account.id != session_accountId:
        return HttpResponseRedirect(reverse('mainapp:home'))

    if session_usertype == "Agent":
        if int(user_id) != request.user.userprofile.id:
            return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        name = request.POST.get('name', "")
        phone = request.POST.get('phone', "")
        email = request.POST.get('email', "").lower()
        email = email.lstrip().rstrip()
        usertype = request.POST.get('usertype', "")
        availability_hours = request.POST.get('availability_hours', "9,18").split(",")
        available = request.POST.get('available', True)

        if len(name)<2:
            return render(request, 'mainapp/edit-user.html', {'error': 'Please enter a name longer than 2 characters', 'userobj':userobj})
        if not is_phone(phone):
            return render(request, 'mainapp/edit-user.html', {'error': 'Please enter a valid phone number', 'userobj':userobj})
        if not is_email(email):
            return render(request, 'mainapp/edit-user.html', {'error': 'Please enter a valid email address', 'userobj':userobj})

        if userobj.usertype != "Owner" and session_usertype != "Agent":
            if usertype not in ["Admin","Agent"]:
                return render(request, 'mainapp/edit-user.html', {'error': 'Please select a user type', 'userobj':userobj})
            else:
                userobj.usertype=usertype

        if available not in ["True","False"]:
            return render(request, 'mainapp/edit-user.html', {'error': 'Please select availability', 'userobj':userobj})

        if email != userobj.user.email:
            if User.objects.filter(email=email).exists():
                return render(request, 'mainapp/edit-user.html', {'error': 'User with this email Id already exists', 'userobj':userobj})
        if phone != userobj.phone:
            if UserProfile.objects.filter(phone=phone).exists():
                return render(request, 'mainapp/edit-user.html', {'error': 'User with this phone number already exists', 'userobj':userobj})

        if phone[0] == "+":
            phone = phone.lstrip("+")

        userobj.name = name
        userobj.phone = phone
        userobj.user.email = email
        userobj.user.username = email
        userobj.available=available
        userobj.sms_missed_calls = False if request.POST.get('sms_missed_calls')==None else True
        userobj.sms_completed_calls  = False if request.POST.get('sms_completed_calls')==None else True
        userobj.sms_new_lead  = False if request.POST.get('sms_new_lead')==None else True
        userobj.email_missed_calls = False if request.POST.get('email_missed_calls')==None else True
        userobj.email_completed_calls = False if request.POST.get('email_completed_calls')==None else True
        userobj.email_new_lead = False if request.POST.get('email_new_lead')==None else True
        userobj.email_widget_daily_reports = False if request.POST.get('email_widget_daily_reports')==None else True
        userobj.email_widget_weekly_reports = False if request.POST.get('email_widget_weekly_reports')==None else True
        userobj.monday = False if request.POST.get('monday') == None else True
        userobj.tuesday = False if request.POST.get('tuesday') == None else True
        userobj.wednesday = False if request.POST.get('wednesday') == None else True
        userobj.thursday = False if request.POST.get('thursday') == None else True
        userobj.friday = False if request.POST.get('friday') == None else True
        userobj.saturday = False if request.POST.get('saturday') == None else True
        userobj.sunday = False if request.POST.get('sunday') == None else True
        userobj.available_from = int(availability_hours[0])
        userobj.available_to = int(availability_hours[1])
        userobj.save()
        userobj.user.save()
        return HttpResponseRedirect(reverse('mainapp:team'))
    else:
        return render(request, 'mainapp/edit-user.html',{'userobj':userobj})


@login_required
def widgets(request):
    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))
    session_accountId = request.user.userprofile.account.id
    session_account = request.user.userprofile.account
    widget = Widget.objects.filter(account=session_account)
    for w in widget:
        q = CallQueue.objects.filter(widget=w).count()
        w.queuecount = q
    return render(request, 'mainapp/widgets.html', {'widget':widget})

@login_required
def widgets_create_new(request):
    session_account = request.user.userprofile.account

    countries = Countries.objects.all()

    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        allowed_countries = json.dumps(request.POST.getlist('countries'))
        print(allowed_countries)
        name = request.POST.get('name', "")
        greeting_text = request.POST.get('greeting_text', "")
        ring_timeout = request.POST.get('ring_timeout', "")

        try:
            ring_timeout = int(ring_timeout)
            if int(ring_timeout) > 120 or int(ring_timeout) < 10:
                ring_timeout = 60
        except:
            ring_timeout = 60

        call_setting = request.POST.get('call_setting', "")
        call_algorithm = request.POST.get('call_algorithm', "")


        if (len(name)<2):
            return render(request, 'mainapp/create_new_widget.html', {'error': 'Please enter a name longer than 2 characters', 'obj': request.POST})
        if call_setting not in["AgentFirst","ClientFirst"]:
            return render(request, 'mainapp/create_new_widget.html', {'error': 'Select a call setting', 'obj': request.POST})
        if call_algorithm not in["Simultaneous","Randomized"]:
            return render(request, 'mainapp/create_new_widget.html', {'error': 'Select a call algorithm', 'obj': request.POST})

        capture_leads = False if request.POST.get('capture_leads')==None else True
        show_on_mobile  = False if request.POST.get('show_on_mobile')==None else True
        Widget.objects.create(account=session_account, name=name ,
                              greeting_text = greeting_text,
                              ring_timeout = ring_timeout,
                              call_setting=call_setting,
                              allowed_countries = allowed_countries,
                              call_algorithm=call_algorithm,
                              capture_leads=capture_leads,
                              show_on_mobile=show_on_mobile)
        return HttpResponseRedirect(reverse('mainapp:widgets'))
    else:
        return render(request, 'mainapp/create_new_widget.html', {"countries":countries})

@login_required
def widget_edit(request, widget_id):
    widgetobj = get_object_or_404(Widget, id=widget_id)

    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    session_accountId = request.user.userprofile.account.id
    if widgetobj.account.id != session_accountId:
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        allowed_countries = request.POST.getlist('countries')
        countries = Countries.objects.all()
        for c in countries:
            if c.country_code in allowed_countries:
                c.selected = True

        print(allowed_countries)
        name = request.POST.get('name', "")
        greeting_text = request.POST.get('greeting_text', "")
        call_setting = request.POST.get('call_setting', "")
        call_algorithm = request.POST.get('call_algorithm', "")
        if (len(name)<2):
            return render(request, 'mainapp/edit-widget.html', {'error': 'Please enter a name longer than 2 characters', 'widgetobj': widgetobj, 'countries':countries})
        if call_setting not in["AgentFirst","ClientFirst"]:
            return render(request, 'mainapp/edit-widget.html', {'error': 'Select a call setting', 'widgetobj': widgetobj, 'countries':countries})
        if call_algorithm not in["Simultaneous","Randomized"]:
            return render(request, 'mainapp/edit-widget.html', {'error': 'Select a call algorithm', 'widgetobj': widgetobj, 'countries':countries})

        ring_timeout = request.POST.get('ring_timeout', "")
        try:
            ring_timeout = int(ring_timeout)
            if int(ring_timeout) > 120 or int(ring_timeout) < 10:
                ring_timeout = 60
        except:
            ring_timeout = 60

        widgetobj.allowed_countries=json.dumps(allowed_countries)
        widgetobj.greeting_text = greeting_text
        widgetobj.ring_timeout = ring_timeout
        widgetobj.call_setting=call_setting
        widgetobj.call_algorithm=call_algorithm
        widgetobj.capture_leads = False if request.POST.get('capture_leads')==None else True
        widgetobj.show_on_mobile = False if request.POST.get('show_on_mobile')==None else True
        widgetobj.save()
        return HttpResponseRedirect(reverse('mainapp:widgets'))
    else:
        countries = Countries.objects.all()
        k = json.loads(widgetobj.allowed_countries)
        for c in countries:
            if c.country_code in k:
                c.selected = True
        return render(request, 'mainapp/edit-widget.html',{'widgetobj':widgetobj, 'countries':countries})

@login_required
def editappearance(request, widget_id):
    widgetobj = get_object_or_404(Widget, id=widget_id)

    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    session_accountId = request.user.userprofile.account.id
    if widgetobj.account.id != session_accountId:
        return HttpResponseRedirect(reverse('mainapp:home'))


    if request.method == 'POST':
        widgetobj.appearance_showalert = False if request.POST.get('appearance_showalert')==None else True
        widgetobj.appearance_showalert_after = request.POST.get('appearance_showalert_after', 3000)
        widgetobj.appearance_playsoundonalert = False if request.POST.get('appearance_playsoundonalert')==None else True
        widgetobj.appearance_alerttext = request.POST.get('appearance_alerttext', "")
        widgetobj.appearance_calltext = request.POST.get('appearance_calltext', "")
        widgetobj.appearance_leadtext = request.POST.get('appearance_leadtext', "")
        widgetobj.appearance_leadthankyoutext = request.POST.get('appearance_leadthankyoutext', "")
        widgetobj.appearance_alert_textcolor = request.POST.get('appearance_alert_textcolor', "")
        widgetobj.appearance_alert_background = request.POST.get('appearance_alert_background', "")
        widgetobj.appearance_body_textcolor = request.POST.get('appearance_body_textcolor', "")
        widgetobj.appearance_body_background = request.POST.get('appearance_body_background', "")
        widgetobj.appearance_position = request.POST.get('appearance_position', "")
        widgetobj.save()
        return render(request, 'mainapp/edit-widgetappearance.html', {'widgetobj': widgetobj, "success":"Saved"})
    else:
        return render(request, 'mainapp/edit-widgetappearance.html', {'widgetobj': widgetobj})


@login_required
def directcall(request, widget_id):
    widgetobj = get_object_or_404(Widget, id =widget_id)
    if django_settings.HOME_URL == "8a3c0b62.ngrok.io":
        homeurl = "http://127.0.0.1:8000"
        link = homeurl+"/static/widget/sdk-l.js"

    if django_settings.HOME_URL == "127.0.0.1:8000":
        homeurl = "http://" + django_settings.HOME_URL
        link = homeurl+"/static/widget/sdk-l.js"

    if django_settings.HOME_URL == "staging.callmenowhq.com":
        homeurl = "https://" + django_settings.HOME_URL
        link = homeurl+"/static/widget/sdk-s.js"

    if django_settings.HOME_URL == "app.callmenowhq.com":
        homeurl = "https://" + django_settings.HOME_URL
        link = homeurl+"/static/widget/sdk.js"
    return render(request, 'mainapp/directcall.html', {'widgetobj': widgetobj, 'link':link})

@login_required
@csrf_exempt
def ajax_widget_agents(request, widget_id):
    widgetobj = get_object_or_404(Widget, id=widget_id)
    session_accountId = request.user.userprofile.account.id
    if widgetobj.account.id != session_accountId:
        return HttpResponseRedirect(reverse('mainapp:home'))

    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        try:
            WidgetAgent.objects.filter(widget=widgetobj).delete()
            print(request.body)
            k = json.loads(request.body.decode('utf-8'))
            for t in k["myarray"]:
                a = WidgetAgent(widget=widgetobj, user=UserProfile.objects.get(id=t))
                a.save()
            return HttpResponse(json.dumps({"success": True}, indent=2))
        except:
            return HttpResponse(json.dumps({"success": False}, indent=2))
    else:
        session_account = request.user.userprofile.account
        team = UserProfile.objects.filter(account=session_account)
        teamobj=[]
        for t in team:
            k = {}
            k["name"] = t.name
            k["usertype"] = t.usertype
            k["id"] = t.id
            if WidgetAgent.objects.filter(user=t, widget=widgetobj).exists():
                k["added"] = True
            else:
                k["added"] = False
            teamobj.append(k)
        return HttpResponse(json.dumps(teamobj))


@login_required
def leads(request):
    session_account = request.user.userprofile.account
    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Owner" or session_usertype =="Admin":
        leads = Leads.objects.filter(account = session_account).order_by('-id')
        print(leads)
    else:
        widgets = Widget.objects.filter(account=session_account)
        list_of_widgets = []
        for w in widgets:
            linked_widgets = WidgetAgent.objects.filter(widget=w, user = request.user.userprofile)
            for l in linked_widgets:
                list_of_widgets.append(l.widget.id)
        print(list_of_widgets)
        leads = Leads.objects.filter(account = session_account, widget_id__in=list_of_widgets).order_by('-id')
        print(leads)
    reader = geolite2.reader()

    today_day = datetime.datetime.now(pytz.timezone(session_account.timezone)).day

    for l in leads:
        country = reader.get(l.ipaddress)
        if country is not None:
            l.country = country["country"]["names"]["en"]
        else:
            l.country = "Not Available"

        if l.datetime.day == today_day:
            l.formatted_day = "Today"
        else:
            if l.datetime.day == (today_day-1):
                l.formatted_day = "Yesterday"
            else:
                l.formatted_day = l.datetime.strftime("%dth %b, %Y")
    return render(request, 'mainapp/leads.html', {"leads":leads})

@login_required
def lead_detail(request, lead_id):
    #Admin and Owner can view all leads for account. Agent can edit leads within the framework of his widgets
    session_account = request.user.userprofile.account
    session_usertype = request.user.userprofile.usertype

    if session_usertype == "Owner" or session_usertype =="Admin":
        lead = Leads.objects.get(account = session_account, id=lead_id)
    else:
        widgets = Widget.objects.filter(account=session_account)
        list_of_widgets = []
        for w in widgets:
            linked_widgets = WidgetAgent.objects.filter(widget=w, user = request.user.userprofile)
            for l in linked_widgets:
                list_of_widgets.append(l.widget.id)
        try:
            lead = Leads.objects.get(account = session_account, id=lead_id, widget_id__in=list_of_widgets)
        except:
            return HttpResponseRedirect(reverse('mainapp:leads'))

    reader = geolite2.reader()
    country = reader.get(lead.ipaddress)
    if country is not None:
        lead.country = country["country"]["names"]["en"]
        lead.city = country["city"]["names"]["en"]
        lead.location = country["location"]
    else:
        lead.country = "Not Available"

    calls = Calls.objects.filter(lead=lead).order_by('-id')
    for call in calls:
        if call.agent == None:
            call.agent_name = "Unassigned"
        else:
            call.agent_name = call.agent.name

    notes = Notes.objects.filter(lead = lead).order_by('-id')
    print("detail view")
    return render(request, 'mainapp/lead-detail.html', {"lead":lead , "calls":calls, "notes":notes})

@login_required
@csrf_exempt
def ajax_edit_lead(request, lead_id):
    session_account = request.user.userprofile.account
    lead = get_object_or_404(Leads, id=lead_id)

    if lead.account != session_account:
        return HttpResponse("Not available")

    if request.method == 'POST':
        name = request.POST.get('name', "")
        email = request.POST.get('email', "").lower()
        email = email.lstrip().rstrip()
        lead_status = request.POST.get('lead_status', "")
        if request.POST.get('phone') == None:
            return HttpResponse(json.dumps({"success": False}, indent=2))
        phone = request.POST['phone']
        if not is_phone(phone):
            return HttpResponse(json.dumps({"success": False}, indent=2))
        if phone[0] == "+":
            phone = phone.lstrip("+")
        lead.name = name
        lead.email= email
        lead.phone = phone
        lead.lead_status = lead_status
        lead.save()
        return HttpResponse(json.dumps({"success":True}, indent=2))
    else:
        message={
            "success" : True,
            "name": lead.name,
            "email" : lead.email,
            "phone" : lead.phone,
            "lead_status" : lead.lead_status
        }
        return HttpResponse(json.dumps(message,indent=2))

#AJAX
@login_required
@csrf_exempt
def add_new_note(request, lead_id):
    leadobj = Leads.objects.get(id=lead_id)
    session_account = request.user.userprofile.account
    if lead.account != session_account:
        return HttpResponse("Not available")

    action = request.POST.get("action", "new")
    print(action)
    if action=="delete":
        try:
            noteobj = Notes.objects.get(id=request.POST['noteid'])
            noteobj.delete()
        except:
            return HttpResponse("error")
    else:
        if int(request.POST['noteid'])==0:
            n = Notes(lead=leadobj , user=request.user.userprofile, text=request.POST['notetext'])
            n.save()
        else:
            noteobj = Notes.objects.get(id=request.POST['noteid'])
            noteobj.text = request.POST['notetext']
            noteobj.save()
    notes = Notes.objects.filter(lead=leadobj).order_by('-id')
    return render(request, 'mainapp/ajax_notes.html', {"notes": notes, "lead":leadobj})


#AJAX
@login_required
def call_from_admin(request, lead_id):
    leadobj = Leads.objects.get(id=lead_id)
    session_account = request.user.userprofile.account
    if lead.account != session_account:
        return HttpResponse("Not available")

    widgetobj = leadobj.widget
    if CallQueue.objects.filter(phone_number=leadobj.phone, widget=widgetobj).count() > 0:
        return HttpResponse(json.dumps({"success":False, "error": "already in queue"}, indent=2))
    uid = uuid.uuid4().hex[:20]
    ipaddress = get_client_ip(request)
    queue = CallQueue(callmenow_uuid=uid, phone_number=leadobj.phone, widget=widgetobj, ipaddress=ipaddress,
                      agent=request.user.userprofile)
    queue.save()
    ProcessNextCall(widgetobj.id)
    return HttpResponse(json.dumps({"success":True, "callmenow_uuid": uid, "status":"call-queued"}, indent=2))

@login_required
def settings(request):
    session_account = request.user.userprofile.account
    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        timezone=request.POST['timezone']
        callerId = request.POST['callerId']

        if len(callerId)>0:
            if not is_phone(callerId):
                return render(request, 'mainapp/settings.html',
                              {'timezones': pytz.common_timezones, 'account': session_account,
                               'error': 'Please enter a valid phone number or empty in Caller Id'})
            else:
                if callerId[0] == "+":
                    callerId = callerId.lstrip("+")

        numberblacklist=request.POST['numberblacklist']
        ipblacklist=request.POST['ipblacklist']

        ips = ipblacklist.split('\r\n')
        for ipaddress in ips:
            if len(ipaddress)>0:
                if not is_ip(ipaddress):
                    return render(request, 'mainapp/settings.html',
                                  {'timezones': pytz.common_timezones, 'account': session_account,
                                   'error': 'Please enter valid IP addresses only'})

        nums = numberblacklist.split('\r\n')
        for n in nums:
            if len(n) > 0:
                if not is_phone(n):
                    return render(request, 'mainapp/settings.html',
                                  {'timezones': pytz.common_timezones, 'account': session_account,
                                   'error': 'Please enter valid phone numbers only'})

        session_account.timezone=timezone
        session_account.callerId = callerId
        session_account.numberblacklist=numberblacklist
        session_account.ipblacklist=ipblacklist
        session_account.save()
        return render(request, 'mainapp/settings.html', {'timezones': pytz.all_timezones, 'account': session_account,
                                            'successmessage':'Saved settings'})
    else:
        return render(request, 'mainapp/settings.html', {'timezones':pytz.all_timezones, 'account':session_account})

@login_required
def referral(request):
    token = request.user.userprofile.account.firstpromoter_authid
    return render(request, 'mainapp/referral.html', {'token':token})

@login_required
def billing(request):
    session_usertype = request.user.userprofile.usertype
    if session_usertype != "Owner":
        return HttpResponseRedirect(reverse('mainapp:home'))
    session_accountId = request.user.userprofile.account.id
    session_account = request.user.userprofile.account
    subs = Subscriptions.objects.filter(callmenow_account = session_account)
    if subs.count()==0:
        return render(request, 'mainapp/billing.html')
    else:
        limits = get_account_limits(session_account)
        plans = Plans.objects.filter(public=True)
        return render(request, 'mainapp/billing_detail.html', {"subscriptions":subs, "plans":plans, "limits":limits})

@login_required
def billing_success(request):
    return render(request, 'mainapp/billing_success.html')

@csrf_exempt
def paddle_webhook(request):
    content = json.dumps(request.POST, indent=2)
    subject = "Paddle Webhook"
    callmenow_email(subject, content, "aditya@impulsemedia.co.in")
    alert_name = request.POST['alert_name']
    if alert_name == "subscription_created":
        callmenow_account = request.POST['passthrough']
        plan_id = request.POST['subscription_plan_id']
        account = Accounts.objects.get(pk=callmenow_account)
        plan = Plans.objects.get(paddle_plan_id=plan_id)
        paddle_subscription_id = request.POST['subscription_id']
        status = request.POST['status']
        cancel_url = request.POST['cancel_url']
        update_url = request.POST['update_url']
        next_bill_date = request.POST['next_bill_date']
        s = Subscriptions.objects.create(callmenow_account = account, plan=plan,
                                         paddle_subscription_id = paddle_subscription_id,
                                         status = status,
                                         cancel_url = cancel_url,
                                         update_url = update_url, next_bill_date=next_bill_date
                                         )
        s.save()
    if alert_name == "subscription_updated":
        paddle_subscription_id = request.POST['subscription_id']
        subscription = Subscriptions.objects.get(paddle_subscription_id=paddle_subscription_id)
        plan_id = request.POST['subscription_plan_id']
        plan = Plans.objects.get(paddle_plan_id=plan_id)
        subscription.status = request.POST['status']
        subscription.next_bill_date = request.POST['next_bill_date']
        subscription.plan = plan
        subscription.save()
    if alert_name == "subscription_cancelled":
        paddle_subscription_id = request.POST['subscription_id']
        subscription = Subscriptions.objects.get(paddle_subscription_id=paddle_subscription_id)
        subscription.status = request.POST['status']
        subscription.save()
    return HttpResponse("")



@csrf_exempt
def available(request, widget_id):
    homeurl = "http://" + django_settings.HOME_URL
    if request.method == 'POST':
        return HttpResponse(json.dumps({"live":False, "error": "Only GET requests"}, indent=2))
    try:
        widgetobj = Widget.objects.get(pk=widget_id)
    except:
        return HttpResponse(json.dumps({"live":False, "error":"Widget Does Not Exist"}, indent=2))

    availability = check_availability(widgetobj)

    try:
        ipaddress = get_client_ip(request)
    except:
        rollbar.report_exc_info()
        ipaddress = "0.0.0.0"

    ips = widgetobj.account.ipblacklist.split('\r\n')
    if ipaddress in ips:
        print("ip blocked")
        return HttpResponse(json.dumps({"live":False, "error": "Black Listed IP Address"}, indent=2))

    country=get_client_country(request)
    k = json.loads(widgetobj.allowed_countries)
    if len(k)>0:
        if country is not None:
            if country not in k:
                return HttpResponse(json.dumps({"live":False, "error": "Country Not Allowed"}, indent=2))

    message={}
    message['country'] = country
    countries=Countries.objects.filter(country_code=country)
    if countries.count()==0:
        message['code'] = ''
    else:
        message['code'] = countries[0]['dial_code']

    message['live'] = True
    message['captureleads'] = widgetobj.capture_leads
    message['showonmobile'] = widgetobj.show_on_mobile
    message['available'] = availability['available']

    k = get_account_limits(widgetobj.account)
    if (k['max_minutes_per_month']*60) < widgetobj.account.usagemeter_seconds:
        message['available'] = False
        message['special_message'] = "Account limit reached"

    message['showalert'] = widgetobj.appearance_showalert
    message['showalert_after'] = widgetobj.appearance_showalert_after
    message['playsoundonalert'] = widgetobj.appearance_playsoundonalert
    message['html'] = "/static/widget/widget.html"
    message['img'] = "/static/widget/"+widgetobj.appearance_buttonimage
    #message['date'] =  ['Today', 'Tomorrow', 'Friday']
    message['time'] = ["8 - 9 AM","9 - 10 AM","10 - 11 AM","11 - 12 AM","12 - 1 PM","1 - 2 PM","2 PM - 3 PM","3 PM - 4 PM","4 PM - 5 PM","5 PM - 6 PM","6 PM - 7 PM","7 PM - 8 PM","8 PM - 9 PM"]
    message['alert'] = {
        'name': '',
        'message': widgetobj.appearance_alerttext,
    }
    message['call'] = {
        'message': widgetobj.appearance_calltext,
    }
    message['lead'] = {
        'message': widgetobj.appearance_leadtext,
    }
    message['style'] = {
        'alert': {
            'color': widgetobj.appearance_alert_textcolor,
            'background': widgetobj.appearance_alert_background,
        },
        'body': {
            'color': widgetobj.appearance_body_textcolor,
            'background': widgetobj.appearance_body_background,
        },
        'position': widgetobj.appearance_position,
    }
    message['queue'] = CallQueue.objects.filter(widget=widgetobj).count()
    return HttpResponse(json.dumps(message, indent=2))

#POST only
@csrf_exempt
def new_lead(request, widget_id):
    if request.method == 'GET':
        return HttpResponse(json.dumps({"status":False, "message": "Only POST requests"}, indent=2))
    try:
        widgetobj = Widget.objects.get(pk=widget_id)
    except:
        return HttpResponse(json.dumps({"status":False, "message":"Widget Does Not Exist"}, indent=2))

    try:
        ipaddress = get_client_ip(request)
    except:
        rollbar.report_exc_info()
        ipaddress = "0.0.0.0"

    ips = widgetobj.account.ipblacklist.split('\r\n')
    if ipaddress in ips:
        return HttpResponse(json.dumps({"status":False, "message": "Black Listed IP address"}, indent=2))

    country=get_client_country(request)
    k = json.loads(widgetobj.allowed_countries)
    if len(k)>0:
        if country is not None:
            if country not in k:
                return HttpResponse(json.dumps({"status":False, "error": "Country Not Allowed"}, indent=2))

    request = json.loads(request.body.decode('utf-8'))

    if 'name' not in request:
        name=""
    else:
        name = request['name']

    if 'email' not in request:
        email=""
    else:
        email = request['email']

    if 'time' not in request:
        time=""
    else:
        time = request['time']

    if 'phone' not in request:
        return HttpResponse(json.dumps({"status":False, "message": "Phone Field Is Required"}, indent=2))
    else:
        phone = request['phone']
        if phone[0] == "+":
            phone = phone.lstrip("+")

    if not is_phone(phone):
        return HttpResponse(json.dumps({"status":False, "message": "Invalid Phone Number"}, indent=2))

    nums = widgetobj.account.numberblacklist.split('\r\n')
    if phone in nums:
        return HttpResponse(json.dumps({"status":False, "message": "Black Listed Phone Number"}, indent=2))

    l = Leads.objects.filter(widget=widgetobj, phone=phone)
    if l.exists():
        lead=l[0]
        lead.name=name
        lead.email=email
        lead.best_time_to_contact=time
        lead.save()
        notify_newlead(lead)
    else:
        #DateTime is stored in database in UTC only.
        a = Leads(widget = widgetobj, account=widgetobj.account , name=name, email=email, phone=phone,
                  best_time_to_contact=time,
                  datetime= datetime.datetime.now(pytz.timezone('UTC')),
                  ipaddress=ipaddress , lead_status="Uncontacted")
        a.save()
        notify_newlead(a)
    message={}
    message['status'] = True
    message['message'] = widgetobj.appearance_leadthankyoutext
    return HttpResponse(json.dumps(message, indent=2))

#POST only
@csrf_exempt
def new_call(request, widget_id):
    if request.method == 'GET':
        return HttpResponse(json.dumps({"callmenow_status":"call-failed", "callmenow_comments": "Only Post Requests"}, indent=2))
    try:
        widgetobj = Widget.objects.get(pk=widget_id)
    except:
        return HttpResponse(json.dumps({"callmenow_status":"call-failed", "callmenow_comments":"Widget ID Does Not Exist"}, indent=2))

    try:
        ipaddress = get_client_ip(request)
    except:
        rollbar.report_exc_info()
        ipaddress = "0.0.0.0"

    ips = widgetobj.account.ipblacklist.split('\r\n')
    if ipaddress in ips:
        return HttpResponse(json.dumps({"callmenow_status":"call-failed", "callmenow_comments": "This IP Address was blacklisted"}, indent=2))

    k = get_account_limits(widgetobj.account)
    if (k['max_minutes_per_month']*60) < widgetobj.account.usagemeter_seconds:
        return HttpResponse(json.dumps({"callmenow_status": "call-failed", "callmenow_comments": "Account usage limit reached"},indent=2))

    country=get_client_country(request)
    k = json.loads(widgetobj.allowed_countries)
    if len(k)>0:
        if country is not None:
            if country not in k:
                return HttpResponse(json.dumps({"callmenow_status":"call-failed", "callmenow_comments": "Country not allowed"}, indent=2))

    request = json.loads(request.body.decode('utf-8'))

    if 'phone' not in request:
        return HttpResponse(json.dumps({"callmenow_status":"call-failed", "callmenow_comments": "Phone Field Is Required"}, indent=2))
    else:
        phone = request['phone']
        if phone[0] == "+":
            phone = phone.lstrip("+")

    if not is_phone(phone):
        return HttpResponse(json.dumps({"callmenow_status":"call-failed", "callmenow_comments": "Invalid Phone Number"}, indent=2))

    widgetagents = WidgetAgent.objects.filter(widget=widgetobj)
    availability = check_availability(widgetobj)

    if availability['available'] == False:
        return HttpResponse(json.dumps({"callmenow_status":"call-failed", "callmenow_comments": "No Agent Available"}, indent=2))

    if CallQueue.objects.filter(phone_number=phone, widget=widgetobj).count() > 0:
        return HttpResponse(json.dumps({"callmenow_status":"call-failed", "callmenow_comments": "Already in Queue"}, indent=2))
    uid = uuid.uuid4().hex[:20]

    nums = widgetobj.account.numberblacklist.split('\r\n')
    if phone in nums:
        return HttpResponse(json.dumps({"callmenow_status":"call-failed", "callmenow_comments": "This phone number was blacklisted"}, indent=2))

    queue = CallQueue(callmenow_uuid=uid, phone_number=phone, widget=widgetobj, ipaddress=ipaddress)
    queue.save()
    ProcessNextCall(widget_id)

    queuecount = CallQueue.objects.filter(widget=widgetobj).count()
    message={}
    message['callmenow_status'] = "call-queued"
    message['callmenow_uuid'] = uid
    message['callmenow_comments'] = "Your call has been queued."
    message['queue'] = queuecount
    return HttpResponse(json.dumps(message, indent=2))

#GET only
@csrf_exempt
def call_status(request, uuid):
    if request.method == 'POST':
        return HttpResponse(json.dumps({"error": "only get requests"}, indent=2))
    try:
        callobj = CallQueue.objects.get(callmenow_uuid=uuid)
        widgetobj = callobj.widget
        queue = CallQueue.objects.filter(widget=widgetobj).order_by('id')
        q = []
        for m in queue:
            q.append(m.id)
        q.sort()
        position=q.index(callobj.id)+1 #zero based index
        return HttpResponse(json.dumps({"callmenow_uuid":uuid , "callmenow_status":"call-queued", "callmenow_comments": "Waiting..", "queue": position}, indent=2))
    except:
        try:
            callobj = Calls.objects.get(callmenow_uuid=uuid)
            return HttpResponse(
                json.dumps({"callmenow_uuid": uuid, "callmenow_status": callobj.callmenow_status, "callmenow_comments":callobj.callmenow_comments}, indent=2))
        except:
            return HttpResponse(json.dumps({"error":"call does not exist"}, indent=2))



def ProcessNextCall(widget_id):
    print("process queue"+str(widget_id))
    homeurl = "http://"+django_settings.HOME_URL
    widgetobj = Widget.objects.get(pk=widget_id)
    if widgetobj.locked==False:
        queuecount = CallQueue.objects.filter(widget=widgetobj).count()
        if queuecount > 0:
            queueobject = CallQueue.objects.filter(widget=widgetobj).order_by('id')[0]
            if queueobject.agent == None:
                availability = check_availability(widgetobj)
                if availability['nonbusy_available'] == False:
                    return

        if queuecount > 0:
            widgetobj.locked=True
            widgetobj.save()
            queueobject= CallQueue.objects.filter(widget=widgetobj).order_by('id')[0]
            leads = Leads.objects.filter(phone=queueobject.phone_number, widget=widgetobj)
            if leads.count() > 0:
                leadobject = leads[0]
            else:
                leadobject = Leads(widget = widgetobj, account=widgetobj.account ,
                                   phone=queueobject.phone_number,
                                   ipaddress=queueobject.ipaddress ,
                                   best_time_to_contact="Not Available", lead_status="Uncontacted")
                leadobject.save()
            if widgetobj.call_setting == "ClientFirst":
                print("client first")
                callobject = Calls(callmenow_uuid = queueobject.callmenow_uuid, lead = leadobject,
                                   widget=widgetobj, agent=queueobject.agent,
                                   account=widgetobj.account,
                                   callmenow_status="call-connecting")
                callobject.save()
                client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID, auth_token=django_settings.PLIVO_AUTH_TOKEN)
                try:
                    answer_url=homeurl+'/plivo/plivo_clientfirst_answer_url/'+queueobject.callmenow_uuid+"/"
                    print(answer_url)
                    if len(widgetobj.account.callerId)>0:
                        callerId = widgetobj.account.callerId
                    else:
                        callerId = widgetobj.account.owner.userprofile.phone
                    print("callerID :"+callerId)
                    print(leadobject.phone)
                    response = client.calls.create(
                        from_=callerId,
                        ring_timeout=widgetobj.ring_timeout,
                        to_=leadobject.phone,
                        answer_url=answer_url,
                        answer_method='POST', )
                except:
                    rollbar.report_exc_info()
                    callobject.callmenow_status="call-failed"
                    callobject.callmenow_comments="Exception: Failed To Call Visitor"
                    callobject.save()
                    queueobject.delete()
                    widgetobj.locked = False
                    widgetobj.save()
                    return
                print(str(response))
                callobject.callmenow_status = "call-connecting"
                callobject.plivo_aleg_call_status = response['message']
                callobject.plivo_aleg_call_id = response['request_uuid']
                callobject.save()
                queueobject.delete()
                return
            if widgetobj.call_setting == "AgentFirst":
                print("agent first")
                callobject = Calls(callmenow_uuid = queueobject.callmenow_uuid, lead = leadobject,
                                   widget=widgetobj, agent=queueobject.agent,
                                   account=widgetobj.account,
                                   callmenow_status="call-connecting")
                callobject.save()
                client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID, auth_token=django_settings.PLIVO_AUTH_TOKEN)

                if callobject.agent == None:
                    print("call from widget")
                    print(widgetobj.call_algorithm)
                    availability=check_availability(widgetobj)
                    list_of_available_agents = availability['list_of_available_nonbusy_agents']
                    print(list_of_available_agents)
                    if widgetobj.call_algorithm == "Simultaneous":
                        listagent_phones=[]
                        for p in availability['list_of_available_nonbusy_agents']:
                            listagent_phones.append(p.phone)
                        k = "<".join(listagent_phones)
                        if len(listagent_phones)==1:
                            callobject.agent=list_of_available_agents[0]
                            callobject.agent.save()
                    if widgetobj.call_algorithm == "Randomized":
                        agent = random.choice(availability['list_of_available_nonbusy_agents'])
                        print("Random agent : " + str(agent))
                        k = agent.phone
                        callobject.agent=agent
                        callobject.agent.save()
                else:
                    print("call from admin")
                    k=callobject.agent.phone
                print("k= " + k)
                try:
                    answer_url=homeurl+'/plivo/plivo_agentfirst_answer_url/'+queueobject.callmenow_uuid+"/"
                    print(answer_url)
                    if len(widgetobj.account.callerId)>0:
                        callerId = widgetobj.account.callerId
                    else:
                        callerId = callobject.lead.phone
                    response = client.calls.create(
                        from_=callerId,
                        ring_timeout=widgetobj.ring_timeout,
                        to_=k,
                        answer_url=answer_url,
                        answer_method='POST', )
                except:
                    rollbar.report_exc_info()
                    callobject.callmenow_status="call-failed"
                    callobject.callmenow_comments="Exception: Failed To Call Manager"
                    callobject.save()
                    queueobject.delete()
                    widgetobj.locked = False
                    widgetobj.save()
                    return
                print(str(response))
                callobject.callmenow_status = "call-connecting"
                callobject.callmenow_comments = "Connecting call"
                callobject.plivo_aleg_call_status = response['message']
                if type(response['request_uuid']) is not list:
                    callobject.agentfirst_aleg_uuids = json.dumps([response['request_uuid']])
                else:
                    callobject.agentfirst_aleg_uuids = json.dumps(response['request_uuid'])
                callobject.save()
                queueobject.delete()
                return


@csrf_exempt
def plivo_clientfirst_answer_url(request,uuid):
    homeurl = "http://" + django_settings.HOME_URL
    print("clientfirst answerurl")
    print(request.body)
    callobject = Calls.objects.get(callmenow_uuid=uuid)
    callobject.plivo_aleg_call_status = request.POST['CallStatus']
    if request.POST['CallStatus']=="busy":
        callobject.callmenow_status="call-failed"
        callobject.plivo_aleg_hangup_cause= request.POST['HangupCause']
        callobject.callmenow_comments = "Visitor's Phone Busy"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['CallStatus']=="failed":
        callobject.callmenow_status="call-failed"
        callobject.plivo_aleg_hangup_cause = request.POST['HangupCause']
        callobject.callmenow_comments = "Failed To Call Visitor"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['CallStatus']=="no-answer":
        callobject.callmenow_status="call-failed"
        callobject.plivo_aleg_hangup_cause = request.POST['HangupCause']
        callobject.callmenow_comments = "Visitor Did Not Answer The Call"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['CallStatus']=="cancel":
        callobject.callmenow_status="call-failed"
        callobject.plivo_aleg_hangup_cause = request.POST['HangupCause']
        callobject.callmenow_comments = "Visitor Cancelled The Call"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['CallStatus']=="timeout":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "Ring timeout"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['Event']=="StartApp":
        widgetobj = callobject.widget
        availablility = check_availability(widgetobj)
        print(availablility)
        list_of_available_agents = availablility['list_of_available_nonbusy_agents']
        print(widgetobj.call_algorithm)
        response = plivoxml.ResponseElement()
        response.add(plivoxml.SpeakElement(widgetobj.greeting_text))

        if callobject.agent == None:
            print("call from widget")
        else:
            print("call from admin")
            list_of_available_agents=[callobject.agent]

        print(list_of_available_agents)
        if widgetobj.call_algorithm == "Simultaneous":
            dial = plivoxml.DialElement(action=homeurl+'/plivo/plivo_clientfirst_dial_url/'+uuid+'/',
                                        method="POST",
                                        callback_url=homeurl+'/plivo/plivo_clientfirst_callback_url/'+uuid+'/',
                                        callback_method="POST",
                                        timeout=widgetobj.ring_timeout,
                                        redirect=False)
            for p in list_of_available_agents:
                dial.add(plivoxml.NumberElement(p.phone))
            response.add(dial)

        if widgetobj.call_algorithm == "Randomized":
            agent = random.choice(list_of_available_agents)
            print("Random agent : "+str(agent))
            dial = plivoxml.DialElement(action=homeurl+'/plivo/plivo_clientfirst_dial_url/'+uuid+'/',
                                        method="POST",
                                        callback_url=homeurl+'/plivo/plivo_clientfirst_callback_url/'+uuid+'/',
                                        callback_method="POST",
                                        timeout=20,
                                        redirect=False)
            dial.add(plivoxml.NumberElement(agent.phone))
            response.add(dial)

        print(response.to_string())
        return HttpResponse(response.to_string())
    if request.POST['Event']=="Hangup":
        print("answerurl-hangup")
        callobject.plivo_aleg_hangup_cause= request.POST['HangupCause']
        callobject.plivo_aleg_duration = request.POST['Duration']
        callobject.plivo_aleg_bill = request.POST['TotalCost']
        total_bill = float(callobject.plivo_aleg_bill) + float(callobject.plivo_bleg_bill)
        print(total_bill)
        print(type(total_bill))
        callobject.total_bill = total_bill
        callobject.widget.locked=False
        try:
            k= callobject.agent
            k.currently_busy=False
            k.save()
        except:
            print("exception setting up agent.currently_busy")
        callobject.widget.save()
        callobject.save()
        return HttpResponse("")

@csrf_exempt
def plivo_clientfirst_dial_url(request, uuid):
    homeurl = "http://" + django_settings.HOME_URL
    print("clientfirst dialurl")
    print(request.body)
    callobject = Calls.objects.get(callmenow_uuid=uuid)
    callobject.plivo_bleg_call_status = request.POST['DialStatus']
    if request.POST['DialStatus']=="failed":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "Unable To Connect With Managers"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['DialStatus']=="no-answer":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "No Manager Answered The Call"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['DialStatus']=="busy":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "Managers Were Busy"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['DialStatus']=="completed":
        callobject.callmenow_status="call-completed"
        callobject.callmenow_comments = "Call completed"
        callobject.lead.lead_status = "Contacted"
        if callobject.lead.owner == None:
            callobject.lead.owner = callobject.agent
        callobject.lead.save()
        try:
            k= callobject.agent
            k.currently_busy=False
            k.save()
        except:
            print("exception setting up agent.currently_busy")
        callobject.widget.locked=False
        callobject.widget.save()
        callobject.save()
        update_usagemeter(callobject)
        notify_completed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")

@csrf_exempt
def plivo_clientfirst_callback_url(request, uuid):
    homeurl = "http://" + django_settings.HOME_URL
    print("clientfirst callbackurl")
    print(request.body)
    callobject = Calls.objects.get(callmenow_uuid=uuid)
    callobject.plivo_bleg_call_id = request.POST['DialBLegUUID']
    callobject.plivo_bleg_call_status = request.POST['DialBLegStatus']
    callobject.save()
    if request.POST['Event']=="DialHangup":
        callobject.plivo_bleg_duration = request.POST['DialBLegDuration']
        callobject.plivo_bleg_hangup_cause = request.POST['DialBLegHangupCause']
        callobject.plivo_bleg_bill = request.POST['DialBLegTotalCost']
        if request.POST['DialBLegHangupCause'] == "ORIGINATOR_CANCEL":
            callobject.callmenow_status = "call-failed"
            callobject.callmenow_comments = "Visitor Cancelled The Call"
            callobject.widget.locked=False
            callobject.widget.save()
            notify_missed_call(callobject)
        callobject.save()
        return HttpResponse("")
    if request.POST['DialAction']=="answer":
        callobject.callmenow_status = "call-inprogress"
        callobject.callmenow_comments = "In Conversation"
        callobject.widget.locked=False
        agentphone = request.POST['DialBLegTo']
        callobject.bleg_phone_number = agentphone
        k= UserProfile.objects.filter(phone=agentphone)[0]
        k.currently_busy=True
        callobject.agent = k
        callobject.save()
        k.save()
        callobject.widget.save()
        ProcessNextCall(callobject.widget.id)
        bleguuid= request.POST["DialBLegUUID"]
        client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID, auth_token=django_settings.PLIVO_AUTH_TOKEN)
        response = client.calls.record(call_uuid=bleguuid,
                                       callback_url=homeurl+'/plivo/plivo_clientfirst_recording_callback_url/'+bleguuid+'/',)
        print(response)
        return HttpResponse("")

    return HttpResponse("")

@csrf_exempt
def plivo_clientfirst_recording_callback_url(request, uuid):
    m = urllib.parse.parse_qs(request.body)
    k = json.loads(m[b'response'][0])
    record_url = k['record_url']
    k = Calls.objects.get(plivo_bleg_call_id = uuid)
    k.record_url = record_url
    k.save()
    print("clientfirst recordurl")
    print(request.method)
    print(uuid)
    print(record_url)
    return HttpResponse("")


@csrf_exempt
def plivo_agentfirst_answer_url(request, uuid):
    homeurl = "http://" + django_settings.HOME_URL
    print("agentfirst answerurl")
    print(request.body)
    callobject = Calls.objects.get(callmenow_uuid=uuid)
    if request.POST['Event']=="StartApp":
        aleg_uuid = request.POST['RequestUUID']
        uuids = json.loads(callobject.agentfirst_aleg_uuids)
        client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID, auth_token=django_settings.PLIVO_AUTH_TOKEN)
        for m in uuids:
            if m != aleg_uuid:
                print("hanging up "+ m)
                response = client.calls.delete(call_uuid=m)
                print(response)
        if callobject.agent == None:
            print("no agent set here")
            agentphone = request.POST['To']
            k = UserProfile.objects.filter(phone=agentphone)[0]
            callobject.agent=k
        else:
            print("agent already set")
        callobject.plivo_aleg_call_id = aleg_uuid
        callobject.agentfirst_aleg_uuids=""
        callobject.plivo_aleg_call_status = request.POST['CallStatus']
        callobject.save()
        response = plivoxml.ResponseElement()
        response.add(plivoxml.SpeakElement(callobject.widget.greeting_text))
        dial = plivoxml.DialElement(action=homeurl + '/plivo/plivo_agentfirst_dial_url/' + uuid + '/',
                                    method="POST",
                                    callback_url=homeurl + '/plivo/plivo_agentfirst_callback_url/' + uuid + '/',
                                    callback_method="POST",
                                    timeout=callobject.widget.ring_timeout,
                                    redirect=False)

        dial.add(plivoxml.NumberElement(callobject.lead.phone))
        response.add(dial)
        print(response.to_string())
        return HttpResponse(response.to_string())
    if request.POST['Event']=="Hangup":
        print("answerurl-hangup")
        if request.POST['RequestUUID'] == callobject.plivo_aleg_call_id:
            print("hanging an ongoing aleg call")
            callobject.plivo_aleg_hangup_cause= request.POST['HangupCause']
            callobject.plivo_aleg_duration = request.POST['Duration']
            callobject.plivo_aleg_bill = request.POST['TotalCost']
            callobject.plivo_aleg_call_status = request.POST['CallStatus']
            total_bill = float(callobject.plivo_aleg_bill) + float(callobject.plivo_bleg_bill)
            print(total_bill)
            print(type(total_bill))
            callobject.total_bill = total_bill
            callobject.widget.locked=False
            callobject.widget.save()
            try:
                k= callobject.agent
                k.currently_busy=False
                k.save()
            except:
                print("exception setting up agent.currently_busy")
            callobject.save()
            ProcessNextCall(callobject.widget.id)
            return HttpResponse("")
        else:
            print("No onongoing aleg: pop this uuid from the list")
            uuids = json.loads(callobject.agentfirst_aleg_uuids)
            uuids.remove(request.POST['RequestUUID'])
            callobject.agentfirst_aleg_uuids=json.dumps(uuids)
            callobject.save()
            if len(uuids) == 0:
                callobject.agentfirst_aleg_uuids=""
                callobject.callmenow_status="call-failed"
                callobject.callmenow_comments="Could Not Connect With Managers"
                callobject.widget.locked = False
                callobject.widget.save()
                try:
                    k = callobject.agent
                    k.currently_busy = False
                    k.save()
                except:
                    print("exception setting up agent.currently_busy")
                callobject.save()
                notify_missed_call(callobject)
                ProcessNextCall(callobject.widget.id)
            return HttpResponse("")

@csrf_exempt
def plivo_agentfirst_dial_url(request, uuid):
    homeurl = "http://" + django_settings.HOME_URL
    print("agentfirst dialurl")
    print(request.body)
    callobject = Calls.objects.get(callmenow_uuid=uuid)
    callobject.plivo_bleg_call_status = request.POST['DialStatus']
    if request.POST['DialStatus']=="failed":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "Could Not Connect With Visitors"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['DialStatus']=="no-answer":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "Visitor Did Not Answer The Call"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['DialStatus']=="busy":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "Visitor's Phone Busy"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        notify_missed_call(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['DialStatus']=="completed":
        callobject.callmenow_status="call-completed"
        callobject.callmenow_comments = "Call completed"
        callobject.lead.lead_status = "Contacted"
        if callobject.lead.owner == None:
            callobject.lead.owner = callobject.agent
        callobject.lead.save()
        try:
            k= callobject.agent
            k.currently_busy=False
            k.save()
        except:
            print("exception setting up agent.currently_busy")
        callobject.widget.locked=False
        callobject.widget.save()
        callobject.save()
        notify_completed_call(callobject)
        update_usagemeter(callobject)
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    return HttpResponse("")

@csrf_exempt
def plivo_agentfirst_callback_url(request, uuid):
    homeurl = "http://" + django_settings.HOME_URL
    print("agentfirst callbackurl")
    print(request.body)
    callobject = Calls.objects.get(callmenow_uuid=uuid)
    callobject.plivo_bleg_call_id = request.POST['DialBLegUUID']
    callobject.plivo_bleg_call_status = request.POST['DialBLegStatus']
    callobject.save()
    if request.POST['Event']=="DialHangup":
        print("hols")
        callobject.plivo_bleg_duration = request.POST['DialBLegDuration']
        callobject.plivo_bleg_hangup_cause = request.POST['DialBLegHangupCause']
        callobject.plivo_bleg_bill = request.POST['DialBLegTotalCost']
        if request.POST['DialBLegHangupCause'] == "ORIGINATOR_CANCEL":
            callobject.callmenow_status = "call-failed"
            callobject.callmenow_comments = "Manager Cancelled The Call"
            callobject.widget.locked=False
            callobject.widget.save()
            notify_missed_call(callobject)
        callobject.save()
        return HttpResponse("")
    if request.POST['DialAction']=="answer":
        callobject.callmenow_status = "call-inprogress"
        callobject.callmenow_comments = "In Conversation"
        callobject.widget.locked=False
        callobject.agent.currently_busy=True
        callobject.save()
        callobject.widget.save()
        ProcessNextCall(callobject.widget.id)
        bleguuid= request.POST["DialBLegUUID"]
        client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID, auth_token=django_settings.PLIVO_AUTH_TOKEN)
        response = client.calls.record(call_uuid=bleguuid,
                                       callback_url=homeurl+'/plivo/plivo_agentfirst_recording_callback_url/'+bleguuid+'/',)
        print(response)
        return HttpResponse("")

    return HttpResponse("")

@csrf_exempt
def plivo_agentfirst_recording_callback_url(request, uuid):
    m = urllib.parse.parse_qs(request.body)
    k = json.loads(m[b'response'][0])
    record_url = k['record_url']
    k = Calls.objects.get(plivo_bleg_call_id = uuid)
    k.record_url = record_url
    k.save()
    print("agentfirst recordurl")
    print(request.method)
    print(uuid)
    print(record_url)
    return HttpResponse("")

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_client_country(request):
    try:
        country = request.META.get('HTTP_CF_IPCOUNTRY')
    except:
        reader = geolite2.reader()
        country = reader.get(get_client_ip(request))
    if country==None:
        reader = geolite2.reader()
        country = reader.get(get_client_ip(request))
    return country

def callmenow_email(subject, html_content, to_email):
    from_email = django_settings.TRANSACTIONAL_FROM_EMAIL
    postmark = PostmarkClient(server_token=django_settings.POSTMARK_TOKEN)
    postmark.emails.send(
        From=from_email,
        To=to_email,
        Subject=subject,
        HtmlBody=html_content
    )

def is_phone(phonenumber):
    try:
        k = int(phonenumber)
        if k>1000000:
            return True
        else:
            return False
    except:
        return False

def is_ip(s):
    a = s.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        i = int(x)
        if i < 0 or i > 255:
            return False
    return True

#Checks agent availability for a widget. Returns a detailed object.
def check_availability(widgetobj):
    widgetagents = WidgetAgent.objects.filter(widget=widgetobj)
    message = {}
    list_of_available_agents = []
    list_of_available_nonbusy_agents = []
    for w in widgetagents:
        profile = w.user
        if profile.available:
            weekday = datetime.datetime.now(pytz.timezone(widgetobj.account.timezone)).weekday()
            hour = datetime.datetime.now(pytz.timezone(widgetobj.account.timezone)).hour
            av=True
            if weekday==0 and profile.monday==False:
                av=False
            if weekday==1 and profile.tuesday==False:
                av=False
            if weekday==2 and profile.wednesday==False:
                av=False
            if weekday==3 and profile.thursday==False:
                av=False
            if weekday==4 and profile.friday==False:
                av=False
            if weekday==5 and profile.saturday==False:
                av=False
            if weekday==6 and profile.sunday==False:
                av=False

            if av:
                if hour >= profile.available_from and hour < profile.available_to:
                    av=True
                else:
                    av=False

                if av == True:
                    list_of_available_agents.append(profile)
                    if not profile.currently_busy:
                        list_of_available_nonbusy_agents.append(profile)

    if len(list_of_available_agents)>0:
        message['available'] = True
    else:
        message['available'] = False

    if len(list_of_available_nonbusy_agents)>0:
        message['nonbusy_available'] = True
    else:
        message['nonbusy_available'] = False

    message['list_of_available_agents'] = list_of_available_agents
    message['list_of_available_nonbusy_agents'] = list_of_available_nonbusy_agents

    print(message)
    return message

def notify_newlead(leadobj):
    widgetagents = WidgetAgent.objects.filter(widget=leadobj.widget)
    for w in widgetagents:
        profile = w.user
        if profile.sms_new_lead:
            client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID,
                                      auth_token=django_settings.PLIVO_AUTH_TOKEN)
            message = "You have a new lead at CallMeNow \n\nContact Number : "+leadobj.phone+"\n\nWidget Name: "+ leadobj.widget.name + "\n\nBest Time To Contact: " + leadobj.best_time_to_contact
            response = client.messages.create(src='16282048694', dst=profile.phone, text=message)
        if profile.email_new_lead:
            reader = geolite2.reader()
            country = reader.get(leadobj.ipaddress)
            try:
                if country["location"]["time_zone"] in pytz.common_timezones:
                    tzone = country["location"]["time_zone"]
                else:
                    tzone = "UTC"
            except:
                tzone = "UTC"

            template = get_template('emails/notify_newlead.html')
            html_content = template.render(
                {"widgetid": leadobj.widget.id,
                 "widgetname": leadobj.widget.name,
                 "leadid": leadobj.id,
                 "phone": leadobj.phone,
                 "date": leadobj.datetime,
                 "best_time" : leadobj.best_time_to_contact,
                 "ipaddress" : leadobj.ipaddress,
                 "timezone": tzone,})
            subject = "New Lead At CallMeNow "+ str(leadobj.id)
            callmenow_email(subject, html_content, profile.user.email)


def notify_missed_call(callobj):
    widgetagents = WidgetAgent.objects.filter(widget=callobj.widget)
    for w in widgetagents:
        profile = w.user
        if profile.sms_missed_calls:
            client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID,
                                      auth_token=django_settings.PLIVO_AUTH_TOKEN)
            message = "You have a new missed call at CallMeNow \n\nContact Number : "+callobj.lead.phone+"\n\nWidget Name: "+ callobj.widget.name
            response = client.messages.create(src='16282048694', dst=profile.phone, text=message)
        if profile.email_missed_calls:
            reader = geolite2.reader()
            country = reader.get(callobj.lead.ipaddress)
            try:
                if country["location"]["time_zone"] in pytz.common_timezones:
                    tzone = country["location"]["time_zone"]
                else:
                    tzone = "UTC"
            except:
                tzone = "UTC"

            template = get_template('emails/notify_missedcall.html')
            html_content = template.render(
                {"widgetid": callobj.widget.id,
                 "widgetname": callobj.widget.name,
                 "leadid": callobj.lead.id,
                 "callid" : callobj.callmenow_uuid,
                 "callmenow_status" : callobj.callmenow_status,
                 "callmenow_comments" : callobj.callmenow_comments,
                 "phone": callobj.lead.phone,
                 "date": callobj.datetime,
                 "ipaddress" : callobj.lead.ipaddress,
                 "timezone": tzone,})
            subject = "New Missed Call At CallMeNow "+callobj.callmenow_uuid
            callmenow_email(subject, html_content, profile.user.email)

def notify_completed_call(callobj):
    widgetagents = WidgetAgent.objects.filter(widget=callobj.widget)
    for w in widgetagents:
        profile = w.user
        if profile.sms_completed_calls:
            client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID,
                                      auth_token=django_settings.PLIVO_AUTH_TOKEN)
            message = "You have a new missed call at CallMeNow \n\nContact Number : "+callobj.lead.phone+"\n\nWidget Name: "+ callobj.widget.name +"\n\nCall Duration: "+ callobj.plivo_aleg_duration
            response = client.messages.create(src='16282048694', dst=profile.phone, text=message)
        if profile.email_completed_calls:
            reader = geolite2.reader()
            country = reader.get(callobj.lead.ipaddress)
            try:
                if country["location"]["time_zone"] in pytz.common_timezones:
                    tzone = country["location"]["time_zone"]
                else:
                    tzone = "UTC"
            except:
                tzone = "UTC"

            template = get_template('emails/notify_completedcall.html')
            html_content = template.render(
                {"widgetid": callobj.widget.id,
                 "widgetname": callobj.widget.name,
                 "leadid": callobj.lead.id,
                 "callid" : callobj.callmenow_uuid,
                 "phone": callobj.lead.phone,
                 "agent": callobj.agent.name,
                 "callmenow_status" : callobj.callmenow_status,
                 "callmenow_comments" : callobj.callmenow_comments,
                 "callduration" : callobj.plivo_aleg_duration,
                 "recordurl" : callobj.record_url,
                 "ipaddress" : callobj.lead.ipaddress,
                 "timezone": tzone,})
            subject = "New Completed Call At CallMeNow "+ callobj.callmenow_uuid
            callmenow_email(subject, html_content, profile.user.email)

def get_account_limits(account):
    message = {}
    if account.accountstatus == "inactive":
        message['max_minutes_per_month'] = 0
        message['max_calls_per_month'] = 0
        message['max_widgets'] = 0
        message['max_users'] = 0
        return message

    if account.accountstatus == "active":
        subs = Subscriptions.objects.filter(callmenow_account = account, status__in=["active","past_due"])
        if subs.count()>0:
            message['max_minutes_per_month'] = 0
            message['max_calls_per_month'] = 0
            message['max_widgets'] = 0
            message['max_users'] = 0
            for s in subs:
                if s.override_max_minutes_per_month > 0:
                    message['max_minutes_per_month'] = message['max_minutes_per_month'] + s.override_max_minutes_per_month
                else:
                    message['max_minutes_per_month'] = message['max_minutes_per_month'] + s.plan.max_minutes_per_month

                if s.override_max_calls_per_month > 0:
                    message['max_calls_per_month'] = message['max_calls_per_month'] + s.override_max_calls_per_month
                else:
                    message['max_calls_per_month'] = message['max_calls_per_month'] + s.plan.max_calls_per_month

                if s.override_max_widgets > 0:
                    message['max_widgets'] = message['max_widgets'] + s.override_max_widgets
                else:
                    message['max_widgets'] = message['max_widgets'] + s.plan.max_widgets

                if s.override_max_users > 0:
                    message['max_users'] = message['max_users'] + s.override_max_users
                else:
                    message['max_users'] = message['max_users'] + s.plan.max_users
        else:
            message['max_minutes_per_month'] = 30
            message['max_calls_per_month'] = 10
            message['max_widgets'] = 5
            message['max_users'] = 5
        return message

def update_usagemeter(callobj):
    session_account = callobj.account
    nowobject = datetime.datetime.now(pytz.timezone(session_account.timezone))
    d = session_account.usagemeter_last_refreshed
    l = nowobject - d
    if l.days > 30:
        session_account.usagemeter_last_refreshed=nowobject
        session_account.usagemeter_seconds = 0
        session_account.usagemeter_calls = 0
        session_account.save()
    session_account.usagemeter_seconds = session_account.usagemeter_seconds + callobj.plivo_bleg_duration
    session_account.usagemeter_calls = session_account.usagemeter_calls + 1
    session_account.save()