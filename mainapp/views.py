from django.shortcuts import render

from django.shortcuts import render, get_object_or_404
from .models import Signups, Accounts, UserProfile, Widget,Plans,Subscriptions, ForgotPassword
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

import datetime
from django.utils import timezone
import pytz





def index(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/app/home')

    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(username=email, password=password)
        if user==None:
            return render(request, 'mainapp/0index.html', {'error':'Cannot login'})
        else:
            #Only users who have an account associated with them can login (Users like django admin etc. not allowed)
            if UserProfile.objects.filter(user=user).count()==1:
                login(request, user)
                return HttpResponseRedirect('/app/home/')
            else:
                return render(request, 'mainapp/0index.html', {'error': 'Not allowed'})

    else:
        return render(request, 'mainapp/0index.html')

def sign_up(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/app/home')

    if request.method == 'POST':
        name=request.POST['name']
        email =request.POST['email']
        phone=request.POST['phone']
        pass1=request.POST['pass1']
        pass2=request.POST['pass2']
        if pass1==pass2:
            if not (User.objects.filter(email=email).exists()):
                uid = uuid.uuid4().hex[:20]
                a = Signups(uuid=uid, name=name, email=email, phone=phone, password=pass1)
                a.save()
                link="http://127.0.0.1:8000/app/emailconfirm/"+uid+"/"
                postmark = PostmarkClient(server_token='a2097480-d252-4c1f-b15a-1bac69c54699')
                #postmark.emails.send(
                #   From='aditya@impulsemedia.co.in',
                #   To=email,
                #   Subject='Please validate your email address',
                #   HtmlBody='Click this link to verify your email address '+ link
                #)
                print(link)
                return render(request, 'mainapp/0checkemail.html')
            else:
                return render(request, 'mainapp/0signup.html', {'error': 'User already exists. Login'})
        else:
            return render(request, 'mainapp/0signup.html', {'error':'Passwords do not match'})
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
    return HttpResponseRedirect('/app/')

def forgotpassword(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/app/home')

    if request.method == 'POST':
        email = request.POST['email']
        user = get_object_or_404(User, email=email)
        uid = uuid.uuid4().hex[:20]
        a = ForgotPassword(uuid=uid, user=user)
        a.save()
        link = "http://127.0.0.1:8000/app/passwordchange/" + uid + "/"
        #postmark = PostmarkClient(server_token='a2097480-d252-4c1f-b15a-1bac69c54699')
        # postmark.emails.send(
        #   From='aditya@impulsemedia.co.in',
        #   To=email,
        #   Subject='Please validate your email address',
        #   HtmlBody='Click this link to verify your email address '+ link
        # )
        print(link)
        return render(request, 'mainapp/0forgot-password.html', {'message':'Please check your email'})
    else:
        return render(request, 'mainapp/0forgot-password.html')

def passwordchange(request, uuid):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/app/home')

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
            return render(request, 'mainapp/0passwordchange.html', {'uuid': uuid, "success": "Password changed"})
    else:
        passobj= get_object_or_404(ForgotPassword, uuid=uuid)
        return render(request, 'mainapp/0passwordchange.html', {'uuid':uuid})

@login_required
def home(request):
    session_usertype = request.user.userprofile.usertype
    session_accountId = request.user.userprofile.account.id
    return render(request, 'mainapp/home.html')

@login_required
def team(request):
    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect('/app/home')

    session_accountId = request.user.userprofile.account.id
    session_account = request.user.userprofile.account

    team = UserProfile.objects.filter(account=session_account)
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

    if request.method == 'POST':
        name = request.POST['name']
        phone = request.POST['phone']
        email = request.POST['email']
        usertype = request.POST['usertype']
        sms_missed_calls = False if request.POST.get('sms_missed_calls')==None else True
        sms_completed_calls  = False if request.POST.get('sms_completed_calls')==None else True
        sms_new_lead  = False if request.POST.get('sms_new_lead')==None else True
        email_missed_calls = False if request.POST.get('email_missed_calls')==None else True
        email_completed_calls = False if request.POST.get('email_completed_calls')==None else True
        email_new_lead = False if request.POST.get('email_new_lead')==None else True
        email_widget_daily_reports = False if request.POST.get('email_widget_daily_reports')==None else True
        email_widget_weekly_reports = False if request.POST.get('email_widget_weekly_reports')==None else True
        if not (User.objects.filter(email=email).exists()):
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
            link = "http://127.0.0.1:8000/app/passwordchange/" + uid + "/"
            print(link)
            postmark = PostmarkClient(server_token='a2097480-d252-4c1f-b15a-1bac69c54699')
            # postmark.emails.send(
            #   From='aditya@impulsemedia.co.in',
            #   To=email,
            #   Subject='You have been invited to CallMeNow',
            #   HtmlBody='Click this link to login '+ link
            # )
            return HttpResponseRedirect('/app/team/')
        else:
            return render(request, 'mainapp/create_new_user.html',{'error':'User with this email Id already exists', 'request':request.POST})
    else:
        return render(request, 'mainapp/create_new_user.html')


@login_required
def team_edit(request,user_id):
    userobj = get_object_or_404(UserProfile, id = user_id)
    session_usertype = request.user.userprofile.usertype
    session_accountId = request.user.userprofile.account.id

    #Admin and Owner can edit profile of all users in their own account.
    #Agent can edit only his own profile
    if userobj.account.id != session_accountId:
        return HttpResponseRedirect('/app/home')

    if session_usertype == "Agent":
        if int(user_id) != request.user.userprofile.id:
            return HttpResponseRedirect('/app/home')

    if request.method == 'POST':
        userobj.name = request.POST['name']
        userobj.phone = request.POST['phone']
        userobj.user.email = request.POST['email']
        userobj.user.username = request.POST['email']

        #Check logic again
        if request.POST.get('usertype') != None:
            userobj.usertype = request.POST['usertype']

        userobj.available=request.POST['available']
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
        return HttpResponseRedirect('/app/team/')
    else:
        return render(request, 'mainapp/edit-user.html',{'userobj':userobj})

@login_required
def widgets(request):
    session_usertype = request.user.userprofile.usertype
    if session_usertype == "Agent":
        return HttpResponseRedirect('/app/home')

    session_accountId = request.user.userprofile.account.id
    session_account = request.user.userprofile.account

    widget = Widget.objects.filter(account=session_account)
    return render(request, 'mainapp/widgets.html', {'widget':widget})

@login_required
def widgets_create_new(request):
    session_account = request.user.userprofile.account
    if request.method == 'POST':
        capture_leads = False if request.POST.get('capture_leads')==None else True
        show_on_mobile  = False if request.POST.get('show_on_mobile')==None else True
        Widget.objects.create(account=session_account, name=request.POST.get('name') ,
                              call_setting=request.POST.get('call_setting'),
                              call_algorithm=request.POST.get('call_algorithm'),
                              capture_leads=capture_leads,
                              show_on_mobile=show_on_mobile)
        return HttpResponseRedirect('/app/widgets/')
    else:
        return render(request, 'mainapp/create_new_widget.html')

@login_required
def widget_edit(request, widget_id):
    widgetobj = Widget.objects.filter(pk=widget_id)[0]
    if request.method == 'POST':
        widgetobj.name = request.POST['name']
        widgetobj.call_setting = request.POST['call_setting']
        widgetobj.call_algorithm = request.POST['call_algorithm']
        widgetobj.capture_leads = False if request.POST.get('capture_leads')==None else True
        widgetobj.show_on_mobile = False if request.POST.get('show_on_mobile')==None else True
        widgetobj.save()
        return HttpResponseRedirect('/app/widgets/')
    else:
        return render(request, 'mainapp/edit-widget.html',{'widgetobj':widgetobj})




@login_required
def myprofile(request):
    return render(request, 'mainapp/leads.html')

@login_required
def leads(request):
    return render(request, 'mainapp/leads.html')

@login_required
def settings(request):
    session_account = request.user.userprofile.account
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
        return HttpResponseRedirect('/app/home')

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
        return HttpResponseRedirect('/app/home')

    session_accountId = request.user.userprofile.account.id
    session_account = request.user.userprofile.account
    planobj = Plans.objects.get(pk=plan_id)

    subs = Subscriptions.objects.filter(accountid=session_accountId, planid=plan_id, current_state='created')
    if subs.exists():
        subsobj = subs[0]
    else:
        client = razorpay.Client(auth=("rzp_test_ohizS8VjORVGAS", "DZdwxoraL5JsjvtKxSVRFzIs"))
        client.set_app_details({"title": "CallMeNow", "version": "1.1"})
        k = client.subscription.create(data={'plan_id' : planobj.razor_pay_planid,
                                        'customer_notify' : 1,
                                        'total_count' : 10
                                         })
        subsobj = Subscriptions.objects.create(planid=plan_id , accountid= session_account,
                                     razorpay_subscription_id= k['id'], current_state=k['status'])


    return render(request, 'mainapp/subscribe.html' , {'plan':planobj, 'subscription':subsobj})


@csrf_exempt
def razorpay_webhook(request):
    d = json.loads(request.body)
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
def answer_url(request):
    print(request.body)
    return HttpResponse("<Response><Speak>Hello Asshole. What are you doing ?</Speak></Response>")
    #return HttpResponse("<Response><Dial><Number>91917503723932</Number></Dial></Response>")

def call(request):
    client = plivo.RestClient(auth_id='MAZJJLMZJLMMQ5MWFHMZ', auth_token='ZTBkZjhhY2M0ZWNkOWFmOTZiZGEzMjM3MDJjZjUx')
    response = client.calls.create(from_='9999799822', to_='9999799833', answer_url='http://9efeca3a.ngrok.io/app/answer_url/')
    print(response)