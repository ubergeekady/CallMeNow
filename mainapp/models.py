from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

# Create your models here.
class Signups(models.Model):
    uuid = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    phone = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.uuid + " - " + self.email

class Accounts(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    accountstatus = models.CharField(max_length=50, default="active")
    timezone = models.CharField(max_length=100, default="GMT")
    ipblacklist=models.TextField(max_length=2000, blank=True)
    numberblacklist = models.TextField(max_length=2000, blank=True)
    callerId = models.CharField(max_length=30, blank=True, null=True, default="")
    onboarded = models.BooleanField(default=False)
    firstpromoter_authid = models.CharField(max_length=100, blank=True, null=True)
    signup_timestamp = models.DateTimeField(default = datetime.now)
    usagemeter_last_refreshed = models.DateTimeField(default = datetime.now)
    usagemeter_seconds = models.IntegerField(default = 0)
    usagemeter_calls = models.IntegerField(default = 0)

    def __str__(self):
        return "Account ID: "+ str(self.pk) + " Owner: "+ self.owner.username

class ForgotPassword(models.Model):
    uuid = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)
    name = models.CharField(max_length=30, blank=False)
    usertype = models.CharField(max_length=30, blank=False)
    phone = models.CharField(max_length=30, blank=False)
    available = models.BooleanField(default=True)
    sms_missed_calls = models.BooleanField(default=False)
    sms_completed_calls = models.BooleanField(default=False)
    sms_new_lead = models.BooleanField(default=False)
    email_missed_calls = models.BooleanField(default=True)
    email_completed_calls = models.BooleanField(default=True)
    email_new_lead = models.BooleanField(default=True)
    email_widget_daily_reports = models.BooleanField(default=False)
    email_widget_weekly_reports = models.BooleanField(default=False)
    available_from = models.IntegerField(default=0)
    available_to = models.IntegerField(default=24)
    monday=models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)
    saturday = models.BooleanField(default=True)
    sunday = models.BooleanField(default=True)
    currently_busy = models.BooleanField(default=False)

    def __str__(self):
        return self.name + " - " + self.user.email


class Widget(models.Model):
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)
    name = models.CharField(max_length=30, blank=False)
    greeting_text = models.CharField(max_length=100, blank=True,null=True)
    call_setting = models.CharField(max_length=30, blank=False)
    call_algorithm = models.CharField(max_length=30, blank=False)
    capture_leads = models.BooleanField(default=False)
    show_on_mobile = models.BooleanField(default=False)
    ring_timeout = models.IntegerField(default = 60)
    allowed_countries = models.CharField(max_length=1000, default="[]")
    locked = models.BooleanField(default=False)
    appearance_showalert  = models.BooleanField(default=True)
    appearance_showalert_after = models.IntegerField(default = 3000)
    appearance_playsoundonalert  = models.BooleanField(default=True)
    appearance_alerttext = models.CharField(max_length=100, default="Hey There! Would You Like To Receive A Call From Us Right Now ?")
    appearance_calltext  = models.CharField(max_length=100, default="Would You Like To Receive A Call From Us Right Now ?")
    appearance_leadtext  = models.CharField(max_length=100, default="We Are Not Around. Please Leave Your Number To Receive A Callback Soon")
    appearance_leadthankyoutext  = models.CharField(max_length=100, default="Thank you, we will get in touch with you soon")
    appearance_alert_textcolor = models.CharField(max_length=50, default="black")
    appearance_alert_background = models.CharField(max_length=50, default="white")
    appearance_body_textcolor = models.CharField(max_length=50, default="black")
    appearance_body_background  = models.CharField(max_length=50, default="white")
    appearance_position = models.CharField(max_length=50, default="right")
    appearance_buttonimage  = models.CharField(max_length=50, default="button1.gif")

    def __str__(self):
        return self.name

class WidgetAgent(models.Model):
    widget = models.ForeignKey(Widget, on_delete=models.CASCADE)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id) + self.user.name

class Plans(models.Model):
    paddle_plan_id = models.IntegerField(blank=False,null=False)
    paddle_plan_name = models.CharField(max_length=100, blank=False, null=False)
    price = models.DecimalField(max_digits=10, default=0, decimal_places=5, blank=True)
    interval = models.CharField(max_length=30, default = "monthly", blank=False, null=False)
    public_description = models.TextField(max_length=1000, blank=True)
    private_description = models.TextField(max_length=1000, blank=True)
    public = models.BooleanField(default=False)
    max_minutes_per_month = models.IntegerField(blank=False,null=False)
    max_calls_per_month = models.IntegerField(blank=False,null=False)
    max_widgets = models.IntegerField(blank=False,null=False)
    max_users = models.IntegerField(blank=False,null=False)

    def __str__(self):
        return self.paddle_plan_name

class Subscriptions(models.Model):
    callmenow_account = models.ForeignKey(Accounts, blank=False, null=False)
    plan = models.ForeignKey(Plans, blank=False, null=False)
    paddle_subscription_id = models.CharField(max_length=100, blank=False)
    status = models.CharField(max_length=100, blank=False)
    cancel_url = models.CharField(max_length=200, blank=False)
    update_url = models.CharField(max_length=200, blank=False)
    next_bill_date = models.CharField(max_length=100, blank=False)
    override_max_minutes_per_month = models.IntegerField(default = 0, blank=False,null=False)
    override_max_calls_per_month = models.IntegerField(default = 0, blank=False,null=False)
    override_max_widgets = models.IntegerField(default = 0, blank=False,null=False)
    override_max_users = models.IntegerField(default = 0, blank=False,null=False)

    def __str__(self):
        return "Subscription: "+ str(self.paddle_subscription_id) + " " + self.status

class Leads(models.Model):
    widget = models.ForeignKey(Widget)
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)
    owner = models.ForeignKey(UserProfile, blank=True, null=True)
    lead_status = models.CharField(max_length=100, blank=False)
    datetime = models.DateTimeField(default = datetime.now)
    name =  models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=100, blank=False)
    email = models.CharField(max_length=100, blank=True)
    best_time_to_contact = models.CharField(max_length=100, blank=True)
    ipaddress = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return "ID:" + str(self.pk) + " Phone: " + self.phone

class Notes(models.Model):
    lead = models.ForeignKey(Leads, on_delete=models.CASCADE)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default = datetime.now)
    text = models.TextField(max_length=1000, blank=True)

class CallQueue(models.Model):
    callmenow_uuid =models.CharField(max_length=100, blank=False)
    phone_number =models.CharField(max_length=100, blank=False)
    widget = models.ForeignKey(Widget, on_delete=models.CASCADE)
    ipaddress = models.CharField(max_length=100, blank=False)
    agent = models.ForeignKey(UserProfile, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return str(self.id) + " " + self.callmenow_uuid + " " + str(self.widget.name) + self.phone_number

class Calls(models.Model):
    callmenow_uuid = models.CharField(max_length=100, blank=False)
    callmenow_comments = models.CharField(max_length=100, blank=True)
    callmenow_status =models.CharField(max_length=100, blank=False)
    agentfirst_aleg_uuids = models.CharField(max_length=500, blank=True)
    lead = models.ForeignKey(Leads, on_delete=models.CASCADE)
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE,blank=True, null=True)
    widget = models.ForeignKey(Widget)
    agent = models.ForeignKey(UserProfile, blank=True, null=True)
    datetime = models.DateTimeField(default = datetime.now)
    plivo_aleg_call_status = models.CharField(max_length=500, blank=True)
    plivo_bleg_call_status = models.CharField(max_length=500, blank=True)
    plivo_aleg_hangup_cause = models.CharField(max_length=500, blank=True)
    plivo_bleg_hangup_cause = models.CharField(max_length=500, blank=True)
    plivo_aleg_call_id = models.CharField(max_length=500, blank=True)
    plivo_bleg_call_id = models.CharField(max_length=500, blank=True)
    plivo_aleg_duration = models.IntegerField(default=0 ,blank=True)
    plivo_bleg_duration = models.IntegerField(default=0, blank=True)
    plivo_aleg_bill = models.DecimalField(max_digits=10, default=0, decimal_places=5, blank=True)
    plivo_bleg_bill = models.DecimalField(max_digits=10, default=0, decimal_places=5, blank=True)
    bleg_phone_number = models.CharField(max_length=500, blank=True)
    record_url = models.CharField(max_length=500, blank=True)
    total_bill = models.DecimalField(max_digits=10, default=0, decimal_places=5, blank=True)

    def __str__(self):
        return self.callmenow_uuid + " " + self.lead.phone

class Countries(models.Model):
    country_name = models.CharField(max_length=100, blank=False)
    country_code = models.CharField(max_length=10, blank=False)
    dial_code = models.IntegerField()