from django.contrib import admin
from .models import Signups, Accounts, UserProfile, Widget, Plans, Subscriptions, ForgotPassword

# Register your models here.
admin.site.register(Signups)
admin.site.register(Accounts)
admin.site.register(UserProfile)
admin.site.register(Widget)
admin.site.register(Plans)
admin.site.register(Subscriptions)
admin.site.register(ForgotPassword)