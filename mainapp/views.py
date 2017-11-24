from django.shortcuts import render

from django.shortcuts import render, get_object_or_404
from .models import Signups, Accounts, UserProfile, \
    Widget,Plans,Subscriptions, ForgotPassword, WidgetAgent, Leads, CallQueue, Calls, Notes
from .forms import WidgetForm
from django.views import generic

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django import forms

from django.http import HttpResponse

from postmarker.core import PostmarkClient
import uuid

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout

import json
import razorpay
import plivo
from plivo import plivoxml
import urllib
from geolite2 import geolite2

import random

import datetime
from django.utils import timezone
import pytz

from django.conf import settings as django_settings
from django.core.mail import send_mail

from django.template.loader import get_template
from django.utils.html import strip_tags
from pyisemail import is_email

from django.core.urlresolvers import reverse


def index(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        email = request.POST['email']
        if not is_email(email):
            return render(request, 'mainapp/0index.html', {'error': 'Invalid Email Address', 'request' : request.POST})

        password = request.POST['password']
        user = authenticate(username=email, password=password)
        if user==None:
            return render(request, 'mainapp/0index.html', {'error':'Could not login', 'request' : request.POST})
        else:
            #Only users who have an account associated with them can login
            # (Users like django admin etc. not allowed)
            if UserProfile.objects.filter(user=user).count()==1:
                login(request, user)
                return HttpResponseRedirect(reverse('mainapp:home'))
            else:
                return render(request, 'mainapp/0index.html', {'error': 'Not allowed', 'request' : request.POST})

    else:
        return render(request, 'mainapp/0index.html')

def sign_up(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        name = request.POST.get('name', "")
        phone = request.POST.get('phone', "")
        email = request.POST.get('email', "")
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

        uid = uuid.uuid4().hex[:20]
        a = Signups(uuid=uid, name=name, email=email, phone=phone, password=pass1)
        a.save()
        link = "https://"+django_settings.HOME_URL+"/emailconfirm/" + uid + "/"
        template = get_template('emails/email_signup.html')
        html_content = template.render({"confirmlink":link})
        subject = "Please validate your email address."
        callmenow_email(subject, html_content, email)
        print(link)
        return render(request, 'mainapp/0signup.html', {'success':True})
    else:
        return render(request, 'mainapp/0signup.html')

def email_confirm(request, uuid):
    signupobj= get_object_or_404(Signups, uuid=uuid)
    User.objects.create_user(signupobj.email, signupobj.email, signupobj.password)
    user = authenticate(username=signupobj.email, password=signupobj.password)
    ac = Accounts.objects.create(owner=user)
    UserProfile.objects.create(user=user, account=ac, name=signupobj.name, usertype='Owner', phone=signupobj.phone)
    signupobj.delete()
    login(request, user)
    return render(request, 'mainapp/0emailverified.html')

def logoutpage(request):
    logout(request)
    return HttpResponseRedirect(reverse('mainapp:index'))

def forgotpassword(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        email = request.POST['email']
        user = get_object_or_404(User, email=email)
        uid = uuid.uuid4().hex[:20]
        a = ForgotPassword(uuid=uid, user=user)
        a.save()
        link = "https://"+django_settings.HOME_URL+"/passwordchange/" + uid + "/"
        template = get_template('emails/email_forgotpassword.html')
        html_content = template.render({"confirmlink":link})
        subject = "Password reset link"
        callmenow_email(subject, html_content, email)
        print(link)
        return render(request, 'mainapp/0forgot-password.html', {'message':'Please check your email and click on the validation link. If you do not recieve the email, please contact support@callmenowhq.com'})
    else:
        return render(request, 'mainapp/0forgot-password.html')

def passwordchange(request, uuid):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        uuid=request.POST['uuid']
        passobj = get_object_or_404(ForgotPassword, uuid=uuid)
        pass1=request.POST['pass1']
        pass2=request.POST['pass2']
        if pass1 != pass2:
            return render(request, 'mainapp/0passwordchange.html', {'uuid': uuid , "error":"Passwords do not match"})
        else:
            passobj.user.set_password(pass1)
            passobj.user.save()
            passobj.delete()
            return render(request, 'mainapp/0passwordchange.html', {'uuid': uuid, "success": "Password changed."})
    else:
        passobj= get_object_or_404(ForgotPassword, uuid=uuid)
        return render(request, 'mainapp/0passwordchange.html', {'uuid':uuid})

@login_required
def home(request):
    #print("hello"+2)
    session_usertype = request.user.userprofile.usertype
    session_account = request.user.userprofile.account
    managers= UserProfile.objects.filter(account=session_account)
    return render(request, 'mainapp/home.html', {"managers":managers})

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
def phoneverify(request, user_id):
    userobj = get_object_or_404(UserProfile, id=user_id)
    action = request.GET['action']
    if action=="initiate":
        digits = random.randrange(1000,9999)
        userobj.verificationcode=digits
        client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID, auth_token=django_settings.PLIVO_AUTH_TOKEN)
        answer_url = homeurl + '/plivo/agent_phone_verification/' + user_id + "/"
        print(answer_url)
        response = client.calls.create(
            from_="919999799833",
            ring_timeout=20,
            to_=userobj.phone,
            answer_url=answer_url,
            answer_method='POST', )
        print(response)
    if action=="verify":
        digits=request.GET['digits']



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
        email = request.POST.get('email', "")
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
        #TODO - phone OTP verification

        user = User.objects.create_user(email, email, 'testpass')
        UserProfile.objects.create(user=user, account=session_account, name=name, usertype=usertype,
            phone=phone, sms_missed_calls = sms_missed_calls,
            sms_completed_calls = sms_completed_calls,
            sms_new_lead = sms_new_lead,
            email_missed_calls = email_missed_calls,
            email_completed_calls = email_completed_calls,
            email_new_lead = email_new_lead,
            email_widget_daily_reports = email_widget_daily_reports,
            email_widget_weekly_reports = email_widget_weekly_reports
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
        email = request.POST.get('email', "")
        usertype = request.POST.get('usertype', "")
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
    return render(request, 'mainapp/widgets.html', {'widget':widget})

@login_required
def widgets_create_new(request):
    session_account = request.user.userprofile.account

    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        name = request.POST.get('name', "")
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
                              call_setting=call_setting,
                              call_algorithm=call_algorithm,
                              capture_leads=capture_leads,
                              show_on_mobile=show_on_mobile)
        return HttpResponseRedirect(reverse('mainapp:widgets'))
    else:
        return render(request, 'mainapp/create_new_widget.html')

@login_required
def widget_edit(request, widget_id):
    widgetobj = Widget.objects.filter(pk=widget_id)[0]

    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        name = request.POST.get('name', "")
        call_setting = request.POST.get('call_setting', "")
        call_algorithm = request.POST.get('call_algorithm', "")
        if (len(name)<2):
            return render(request, 'mainapp/edit-widget.html', {'error': 'Please enter a name longer than 2 characters', 'widgetobj': widgetobj})
        if call_setting not in["AgentFirst","ClientFirst"]:
            return render(request, 'mainapp/edit-widget.html', {'error': 'Select a call setting', 'widgetobj': widgetobj})
        if call_algorithm not in["Simultaneous","Randomized"]:
            return render(request, 'mainapp/edit-widget.html', {'error': 'Select a call algorithm', 'widgetobj': widgetobj})
        widgetobj.call_setting=call_setting
        widgetobj.call_algorithm=call_algorithm
        widgetobj.capture_leads = False if request.POST.get('capture_leads')==None else True
        widgetobj.show_on_mobile = False if request.POST.get('show_on_mobile')==None else True
        widgetobj.save()
        return HttpResponseRedirect(reverse('mainapp:widgets'))
    else:
        return render(request, 'mainapp/edit-widget.html',{'widgetobj':widgetobj})


@login_required
@csrf_exempt
def ajax_widget_agents(request, widget_id):
    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        try:
            widgetobj = get_object_or_404(Widget, id=widget_id)
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
        widgetobj = get_object_or_404(Widget, id = widget_id)
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
        leads = Leads.objects.filter(account = session_account)
        print(leads)
    else:
        widgets = Widget.objects.filter(account=session_account)
        list_of_widgets = []
        for w in widgets:
            linked_widgets = WidgetAgent.objects.filter(widget=w, user = request.user.userprofile)
            for l in linked_widgets:
                list_of_widgets.append(l.widget.id)
        print(list_of_widgets)
        leads = Leads.objects.filter(account = session_account, widget_id__in=list_of_widgets)
        print(leads)
    reader = geolite2.reader()
    for l in leads:
        country = reader.get(l.ipaddress)
        if country is not None:
            l.country = country["country"]["names"]["en"]
        else:
            l.country = "Not Available"
    return render(request, 'mainapp/leads.html', {"leads":leads})

@login_required
def lead_detail(request, lead_id):
    #Admin and Owner can view all leads for account. Agent can edit leads within the framework of his widgets
    session_account = request.user.userprofile.account
    session_usertype = request.user.userprofile.usertype

    if session_usertype == "Owner" or session_usertype =="Admin":
        lead = Leads.objects.get(id=lead_id)
    else:
        widgets = Widget.objects.filter(account=session_account)
        list_of_widgets = []
        for w in widgets:
            linked_widgets = WidgetAgent.objects.filter(widget=w, user = request.user.userprofile)
            for l in linked_widgets:
                list_of_widgets.append(l.widget.id)
        try:
            lead = Leads.objects.get(id=lead_id, widget_id__in=list_of_widgets)
        except:
            return HttpResponseRedirect(reverse('mainapp:leads'))

    reader = geolite2.reader()
    country = reader.get(lead.ipaddress)
    if country is not None:
        lead.country = country["country"]["names"]["en"]
    else:
        lead.country = "Not Available"

    calls = Calls.objects.filter(lead=lead).order_by('id')
    for call in calls:
        if call.agent == None:
            call.agent_name = "Unassigned"
        else:
            call.agent_name = call.agent.name

    notes = Notes.objects.filter(lead = lead)
    print("detail view")
    return render(request, 'mainapp/lead-detail.html', {"lead":lead , "calls":calls, "notes":notes})

#AJAX
@login_required
@csrf_exempt
def add_new_note(request, lead_id):
    #TODO Security flaw
    leadobj = Leads.objects.get(id=lead_id)
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
    notes = Notes.objects.filter(lead=leadobj)
    return render(request, 'mainapp/ajax_notes.html', {"notes": notes, "lead":leadobj})


#AJAX
@login_required
def call_from_admin(request, lead_id):
    leadobj = get_object_or_404(Leads, id=lead_id)
    widgetobj = leadobj.widget
    if CallQueue.objects.filter(phone_number=leadobj.phone, widget=widgetobj).count() > 0:
        return HttpResponse(json.dumps({"success": False}, indent=2))
    uid = uuid.uuid4().hex[:20]
    ipaddress = get_client_ip(request)
    queue = CallQueue(callmenow_uuid=uid, phone_number=leadobj.phone, widget=widgetobj, ipaddress=ipaddress,
                      agent=request.user.userprofile)
    queue.save()
    ProcessNextCall(widgetobj.id)
    return HttpResponse(json.dumps({"success": True}, indent=2))

@login_required
def settings(request):
    session_account = request.user.userprofile.account
    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect(reverse('mainapp:home'))

    if request.method == 'POST':
        timezone=request.POST['timezone']
        numberblacklist=request.POST['numberblacklist']
        ipblacklist=request.POST['ipblacklist']
        session_account.timezone=timezone
        session_account.numberblacklist=numberblacklist
        session_account.ipblacklist=ipblacklist
        session_account.save()
        return render(request, 'mainapp/settings.html', {'timezones': pytz.all_timezones, 'account': session_account,
                                            'successmessage':'Saved settings'})
    else:
        return render(request, 'mainapp/settings.html', {'timezones':pytz.all_timezones, 'account':session_account})

@login_required
def billing(request):
    session_usertype = request.user.userprofile.usertype
    if session_usertype != "Owner":
        return HttpResponseRedirect(reverse('mainapp:home'))

    session_accountId = request.user.userprofile.account.id
    session_account = request.user.userprofile.account

    if session_account.accounttype != "Free":
        subid = session_account.subscriptionid
        subobj = Subscriptions.objects.filter(razorpay_subscription_id=subid)[0]
        planid = subobj.planid
        planobj = Plans.objects.filter(id=planid)[0]
    else:
        subobj={}
        planobj={}

    return render(request, 'mainapp/billing.html', {'account':session_account , 'subobj':subobj, 'planobj':planobj})

@login_required
def subscribe(request, plan_id):
    session_usertype = request.user.userprofile.usertype
    if session_usertype != "Owner":
        return HttpResponseRedirect(reverse('mainapp:home'))

    session_accountId = request.user.userprofile.account.id
    session_account = request.user.userprofile.account
    planobj = Plans.objects.get(pk=plan_id)

    subs = Subscriptions.objects.filter(account=session_accountId, planid=plan_id, current_state='created')
    if subs.exists():
        subsobj = subs[0]
    else:
        client = razorpay.Client(auth=("rzp_test_ohizS8VjORVGAS", "DZdwxoraL5JsjvtKxSVRFzIs"))
        client.set_app_details({"title": "CallMeNow", "version": "1.1"})
        k = client.subscription.create(data={'plan_id' : planobj.razor_pay_planid,
                                        'customer_notify' : 1,
                                        'total_count' : 10
                                         })
        subsobj = Subscriptions.objects.create(planid=plan_id , account= session_account,
                                     razorpay_subscription_id= k['id'], current_state=k['status'])


    return render(request, 'mainapp/subscribe.html' , {'plan':planobj, 'subscription':subsobj})


@csrf_exempt
def razorpay_webhook(request):
    k = json.loads(request.body.decode('utf-8'))
    print(json.dumps(d))
    print(d['payload']['subscription']['entity']['status'])

    if d['event']=="subscription.activated":
        id = d['payload']['subscription']['entity']['id']
        subs = Subscriptions.objects.filter(razorpay_subscription_id=id)[0]
        subs.current_state=d['payload']['subscription']['entity']['status']
        subs.accountid.accounttype='Paid'
        subs.accountid.planid= Plans.objects.filter(razor_pay_planid=d['payload']['subscription']['entity']['plan_id'])[0].id
        subs.accountid.subscriptionid = d['payload']['subscription']['entity']['id']
        subs.save()
        subs.accountid.save()

    return HttpResponse("")







@csrf_exempt
def available(request, widget_id):
    if request.method == 'POST':
        return HttpResponse(json.dumps({"error": "only get requests"}, indent=2))
    try:
        widgetobj = Widget.objects.get(pk=widget_id)
    except:
        return HttpResponse(json.dumps({"error":"widget does not exist"}, indent=2))
    widgetagents = WidgetAgent.objects.filter(widget=widgetobj)
    list_of_available_agents = []
    for w in widgetagents:
        profile = w.user
        if profile.available:
            list_of_available_agents.append(w.user.id)

    message={}
    message['live'] = True
    message['captureleads'] = widgetobj.capture_leads
    message['showonmobile'] = widgetobj.show_on_mobile
    if len(list_of_available_agents) > 0:
        message['available'] = True
    else:
        message['available'] = False
    #Number of items in queue
    message['queue'] = CallQueue.objects.filter(widget=widgetobj).count()
    return HttpResponse(json.dumps(message, indent=2))

#POST only
@csrf_exempt
def new_lead(request, widget_id):
    #IF lead with this phone number AND belongs to this widget exists. Merge with existing lead.
    if request.method == 'GET':
        return HttpResponse(json.dumps({"error": "only post requests"}, indent=2))
    try:
        widgetobj = Widget.objects.get(pk=widget_id)
    except:
        return HttpResponse(json.dumps({"error":"widget does not exist"}, indent=2))
    name = request.POST.get('name', "")
    email = request.POST.get('email', "")
    best_time = request.POST.get('best_time_to_contact', "00:00:00")
    if request.POST.get('phone') == None:
        return HttpResponse(json.dumps({"error":"phone field is required"}, indent=2))
    phone = request.POST['phone']
    if not is_phone(phone):
        return HttpResponse(json.dumps({"error": "Invalid phone number"}, indent=2))
    ipaddress = get_client_ip(request)
    l = Leads.objects.filter(widget=widgetobj, phone=phone)
    if l.exists():
        lead=l[0]
        lead.name=name
        lead.email=email
        lead.best_time_to_contact=best_time
        lead.save()
    else:
        a = Leads(widget = widgetobj, account=widgetobj.account , name=name, email=email, phone=phone,
                  best_time_to_contact=best_time, ipaddress=ipaddress , lead_status="Uncontacted")
        a.save()
    message={}
    message['success']=True
    return HttpResponse(json.dumps(message, indent=2))

#POST only
@csrf_exempt
def new_call(request, widget_id):
    if request.method == 'GET':
        return HttpResponse(json.dumps({"error": "only post requests"}, indent=2))
    try:
        widgetobj = Widget.objects.get(pk=widget_id)
    except:
        return HttpResponse(json.dumps({"error":"widget does not exist"}, indent=2))
    if request.POST.get('phone') == None:
        return HttpResponse(json.dumps({"error":"phone field is required"}, indent=2))
    phone = request.POST['phone']
    if not is_phone(phone):
        return HttpResponse(json.dumps({"error": "Invalid phone number"}, indent=2))
    widgetagents = WidgetAgent.objects.filter(widget=widgetobj)
    list_of_available_agents = []
    for w in widgetagents:
        profile = w.user
        if profile.available:
            list_of_available_agents.append(w.user.id)
    if len(list_of_available_agents) == 0:
        return HttpResponse(json.dumps({"error": "no agent available"}, indent=2))
    if CallQueue.objects.filter(phone_number=phone, widget=widgetobj).count() > 0:
        return HttpResponse(json.dumps({"error": "already in queue"}, indent=2))
    uid = uuid.uuid4().hex[:20]
    ipaddress = get_client_ip(request)
    queue = CallQueue(callmenow_uuid=uid, phone_number=phone, widget=widgetobj, ipaddress=ipaddress)
    queue.save()
    ProcessNextCall(widget_id)
    return HttpResponse(json.dumps({"callmenow_uuid": uid, "status":"call-queued"}, indent=2))

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
        return HttpResponse(json.dumps({"callmenow_uuid":uuid , "callmenow_status":"call-queued", "queue": position}, indent=2))
    except:
        try:
            callobj = Calls.objects.get(callmenow_uuid=uuid)
            return HttpResponse(
                json.dumps({"callmenow_uuid": uuid, "callmenow_status": callobj.callmenow_status}, indent=2))
        except:
            return HttpResponse(json.dumps({"error":"call does not exist"}, indent=2))



def ProcessNextCall(widget_id):
    print("process queue"+str(widget_id))
    homeurl = "http://"+django_settings.HOME_URL
    widgetobj = Widget.objects.get(pk=widget_id)
    #Are there any calls in queue for this widget and the widget is not locked currently.
    if widgetobj.locked==False:

        #Atleast 1 non-busy agent available. Else return.
        widgetagents = WidgetAgent.objects.filter(widget=widgetobj)
        list_of_available_agents = []
        for w in widgetagents:
            profile = w.user
            if profile.available and not profile.currently_busy:
                list_of_available_agents.append(profile)

        if len(list_of_available_agents)==0:
            return

        if CallQueue.objects.filter(widget=widgetobj).count() > 0:
            widgetobj.locked=True
            widgetobj.save()
            #Pick up the next call from the queue for this widget
            queueobject= CallQueue.objects.filter(widget=widgetobj).order_by('id')[0]
            #If a lead does not exist for this customer phone, AND this widget then create it.
            #Otherwise retrieve the lead object
            leads = Leads.objects.filter(phone=queueobject.phone_number, widget=widgetobj)
            if leads.count() > 0:
                leadobject = leads[0]
            else:
                leadobject = Leads(widget = widgetobj, account=widgetobj.account ,
                                   phone=queueobject.phone_number,
                                   ipaddress=queueobject.ipaddress ,
                                   best_time_to_contact="00:00:00", lead_status="Uncontacted")
                leadobject.save()
            #Create the call, delete from queue and fire the call now
            if widgetobj.call_setting == "ClientFirst":
                print("client first")
                callobject = Calls(callmenow_uuid = queueobject.callmenow_uuid, lead = leadobject,
                                   widget=widgetobj, agent=queueobject.agent,
                                   callmenow_status="call-connecting")
                callobject.save()
                client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID, auth_token=django_settings.PLIVO_AUTH_TOKEN)
                try:
                    answer_url=homeurl+'/plivo/plivo_clientfirst_answer_url/'+queueobject.callmenow_uuid+"/"
                    print(answer_url)
                    response = client.calls.create(
                        from_=widgetobj.account.owner.userprofile.phone,
                        ring_timeout=20,
                        to_=leadobject.phone,
                        answer_url=answer_url,
                        answer_method='POST', )
                except:
                    print("exception1")
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
                                   callmenow_status="call-connecting")
                callobject.save()
                client = plivo.RestClient(auth_id=django_settings.PLIVO_AUTH_ID, auth_token=django_settings.PLIVO_AUTH_TOKEN)

                if callobject.agent == None:
                    widgetagents = WidgetAgent.objects.filter(widget=widgetobj)
                    print("call from widget")
                    print("widgetagents = " + str(widgetagents))
                    list_of_available_agents = []
                    for w in widgetagents:
                        profile = w.user
                        if profile.available and not profile.currently_busy:
                            list_of_available_agents.append(profile)
                    print(widgetobj.call_algorithm)
                    print(list_of_available_agents)
                    if widgetobj.call_algorithm == "Simultaneous":
                        listagent_phones = []
                        for p in list_of_available_agents:
                            listagent_phones.append(p.phone)
                        k = "<".join(listagent_phones)
                        if len(listagent_phones)==1:
                            callobject.agent=list_of_available_agents[0]
                            callobject.agent.save()
                    if widgetobj.call_algorithm == "Randomized":
                        agent = random.choice(list_of_available_agents)
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
                    response = client.calls.create(
                        from_=callobject.lead.phone,
                        ring_timeout=20,
                        to_=k,
                        answer_url=answer_url,
                        answer_method='POST', )
                except:
                    print("exception1")
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
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['CallStatus']=="failed":
        callobject.callmenow_status="call-failed"
        callobject.plivo_aleg_hangup_cause = request.POST['HangupCause']
        callobject.callmenow_comments = "Failed To Call Visitor"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['CallStatus']=="no-answer":
        callobject.callmenow_status="call-failed"
        callobject.plivo_aleg_hangup_cause = request.POST['HangupCause']
        callobject.callmenow_comments = "Visitor Did Not Answer The Call"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['CallStatus']=="cancel":
        callobject.callmenow_status="call-failed"
        callobject.plivo_aleg_hangup_cause = request.POST['HangupCause']
        callobject.callmenow_comments = "Visitor Cancelled The Call"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['CallStatus']=="timeout":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "Ring timeout"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['Event']=="StartApp":
        widgetagents = WidgetAgent.objects.filter(widget=callobject.widget)
        print("h1")
        print(widgetagents)
        list_of_available_agents = []
        for w in widgetagents:
            profile = w.user
            if profile.available and not profile.currently_busy:
                list_of_available_agents.append(profile)

        widgetobj = callobject.widget
        print(widgetobj.call_algorithm)
        response = plivoxml.ResponseElement()
        response.add(plivoxml.SpeakElement("Please wait while we transfer your call"))

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
                                        timeout=20,
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
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['DialStatus']=="no-answer":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "No Manager Answered The Call"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['DialStatus']=="busy":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "Managers Were Busy"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
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
        #What if the same number is in other account. This should not be possible in the application.
        #But this can be an error point.
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
        response.add(plivoxml.SpeakElement("Please wait while we transfer your call"))
        dial = plivoxml.DialElement(action=homeurl + '/plivo/plivo_agentfirst_dial_url/' + uuid + '/',
                                    method="POST",
                                    callback_url=homeurl + '/plivo/plivo_agentfirst_callback_url/' + uuid + '/',
                                    callback_method="POST",
                                    timeout=20,
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
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['DialStatus']=="no-answer":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "Visitor Did Not Answer The Call"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
        ProcessNextCall(callobject.widget.id)
        return HttpResponse("")
    if request.POST['DialStatus']=="busy":
        callobject.callmenow_status="call-failed"
        callobject.callmenow_comments = "Visitor's Phone Busy"
        callobject.widget.locked=False
        callobject.save()
        callobject.widget.save()
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

def callmenow_email(subject, html_content, to_email):
    from_email = django_settings.TRANSACTIONAL_FROM_EMAIL
    #text_content = strip_tags(html_content)
    # send_mail(
    #    subject=subject,
    #    message = text_content,
    #    html_message=html_content,
    #    from_email = from_email,
    #    recipient_list=[to_email],
    #    fail_silently=False,
    #)
    postmark = PostmarkClient(server_token=django_settings.POSTMARK_TOKEN)
    postmark.emails.send(
        From=from_email,
        To=to_email,
        Subject=subject,
        HtmlBody=html_content
    )

def is_phone(phonenumber):
    #to check for valid phone numbers
    #currently only checks if it is a number greater than 10000000 (minumum 8 digits and a number)
    try:
        k = int(phonenumber)
        if k>1000000:
            return True
        else:
            return False
    except:
        return False