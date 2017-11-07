from django.db import models
from django.contrib.auth.models import User


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
    available = models.BooleanField(default=True)
    sms_missed_calls = models.BooleanField(default=False)
    sms_completed_calls = models.BooleanField(default=False)
    sms_new_lead = models.BooleanField(default=False)
    email_missed_calls = models.BooleanField(default=False)
    email_completed_calls = models.BooleanField(default=False)
    email_new_lead = models.BooleanField(default=False)
    email_widget_daily_reports = models.BooleanField(default=False)
    email_widget_weekly_reports = models.BooleanField(default=False)

    def __str__(self):
        return self.name + " - " + self.user.email


class Widget(models.Model):
    account = models.ForeignKey(Accounts, on_delete=models.CASCADE)
    name = models.CharField(max_length=30, blank=False)
    call_setting = models.CharField(max_length=30, blank=False)
    call_algorithm = models.CharField(max_length=30, blank=False)
    capture_leads = models.BooleanField(default=False)
    show_on_mobile = models.BooleanField(default=False)

    def __str__(self):
        return self.name


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
    accountid = models.ForeignKey(Accounts, on_delete=models.CASCADE)
    razorpay_subscription_id=models.CharField(max_length=100, blank=False)
    current_state=models.CharField(max_length=100, blank=False)

    def __str__(self):
        return str(self.pk) + " " + self.current_state