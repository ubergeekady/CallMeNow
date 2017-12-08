from django.contrib import admin
from .models import Signups, Accounts, UserProfile, Widget, Plans, \
    Subscriptions, ForgotPassword, WidgetAgent,Leads, CallQueue, Calls, Notes, Countries
from django.forms import TextInput
from django.db import models


@admin.register(Accounts)
class AccountsAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'accountstatus')

@admin.register(Signups)
class SignupsAdmin(admin.ModelAdmin):
    list_display = ('uuid','name','email','phone')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display=('id', 'user','account','name','usertype','phone')

@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ('id','account','name','locked')

@admin.register(Plans)
class PlansAdmin(admin.ModelAdmin):
    list_display = ('paddle_plan_id','paddle_plan_name','public','price', 'interval', 'max_minutes_per_month','max_calls_per_month','max_widgets','max_users')

@admin.register(Subscriptions)
class SubscriptionsAdmin(admin.ModelAdmin):
    list_display = ('callmenow_account','plan','paddle_subscription_id','status','next_bill_date','override_max_minutes_per_month','override_max_calls_per_month')

@admin.register(ForgotPassword)
class ForgotPasswordAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'user')

@admin.register(WidgetAgent)
class WidgetAgentAdmin(admin.ModelAdmin):
    list_display = ('id','widget','user')

@admin.register(Leads)
class LeadsAdmin(admin.ModelAdmin):
    list_display = ('id','widget','account','phone','lead_status','datetime')

@admin.register(CallQueue)
class CallQueueAdmin(admin.ModelAdmin):
    list_display = ('id','callmenow_uuid','phone_number','widget','agent','ipaddress')

@admin.register(Calls)
class CallsAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'100'})},
    }
    list_display = ('callmenow_uuid','callmenow_status','callmenow_comments','lead','widget','datetime')

@admin.register(Notes)
class NotesAdmin(admin.ModelAdmin):
    list_display = ('lead','user','timestamp','text')

@admin.register(Countries)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('country_name','country_code','dial_code')
