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
    accounttype = models.CharField(max_length=100, default="Free")
    planid = models.CharField(max_length=100, null=True)
    subscriptionid = models.CharField(max_length=100, null=True)
    timezone = models.CharField(max_length=100, default="GMT")
    ipblacklist=models.TextField(max_length=1000, blank=True)
    numberblacklist = models.TextField(max_length=1000, blank=True)

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
    verified = models.BooleanField(default=False)
    verificationcode = models.IntegerField(null=True, blank=True)
    available = models.BooleanField(default=True)
    sms_missed_calls = models.BooleanField(default=False)
    sms_completed_calls = models.BooleanField(default=False)
    sms_new_lead = models.BooleanField(default=False)
    email_missed_calls = models.BooleanField(default=False)
    email_completed_calls = models.BooleanField(default=False)
    email_new_lead = models.BooleanField(default=False)
    email_widget_daily_reports = models.BooleanField(default=False)
    email_widget_weekly_reports = models.BooleanField(default=False)
    currently_busy = models.BooleanField(default=False)

    def __str__(self):
        return self.name + " - " + self.user.email


class Widget(models.Model):
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)
    name = models.CharField(max_length=30, blank=False)
    call_setting = models.CharField(max_length=30, blank=False)
    call_algorithm = models.CharField(max_length=30, blank=False)
    capture_leads = models.BooleanField(default=False)
    show_on_mobile = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class WidgetAgent(models.Model):
    widget = models.ForeignKey(Widget, on_delete=models.CASCADE)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)


class Plans(models.Model):
    plan_name = models.CharField(max_length=100, blank=False)
    plan_description = models.TextField(max_length=1000)
    widgets = models.IntegerField(blank=False)
    users = models.IntegerField(blank=False)
    calls = models.IntegerField(blank=False)
    price_usd = models.IntegerField(blank=False)
    price_inr = models.IntegerField(blank=False)
    razor_pay_planid = models.CharField(max_length=100, blank=False)
    admin_notes = models.TextField(max_length=1000, blank=True)

    def __str__(self):
        return self.plan_name

class Subscriptions(models.Model):
    planid = models.IntegerField(blank=False)
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)
    razorpay_subscription_id=models.CharField(max_length=100, blank=False)
    current_state=models.CharField(max_length=100, blank=False)

    def __str__(self):
        return str(self.pk) + " " + self.current_state

class Leads(models.Model):
    widget = models.ForeignKey(Widget)
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)
    owner = models.ForeignKey(UserProfile, blank=True, null=True)
    lead_status = models.CharField(max_length=100, blank=False)
    datetime = models.DateTimeField(default = datetime.now)
    name =  models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=100, blank=False)
    email = models.CharField(max_length=100, blank=True)
    best_time_to_contact = models.TimeField(blank=True)
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
