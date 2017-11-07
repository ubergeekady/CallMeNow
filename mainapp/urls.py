from django.conf.urls import url, include
from django.contrib.auth import views as auth_views
from . import views

#For namespacing the urls in this app.
app_name = 'mainapp'

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^sign-up/', views.sign_up, name='sign_up'),
    url(r'^emailconfirm/(?P<uuid>[-\w]+)/$', views.email_confirm, name='email_confirm'),
    url(r'^logout/$', views.logoutpage,  name='logout'),
    url(r'^forgotpassword/', views.forgotpassword, name='forgotpassword'),
    url(r'^passwordchange/(?P<uuid>[-\w]+)/$', views.passwordchange, name='passwordchange'),
    url(r'^home/', views.home, name='home'),
    url(r'^team/$', views.team, name='team'),
    url(r'^team/create-new/', views.team_create_new, name='team_create_new'),
    url(r'^team/toggleavailability/(?P<user_id>[-\w]+)/(?P<value>[-\w]+)', views.toggleavailability, name='toggleavailability'),
    url(r'^team/edit/(?P<user_id>[0-9]+)/$', views.team_edit, name='team_edit'),
    url(r'^widgets/$', views.widgets, name='widgets'),
    url(r'^widgets/create-new/', views.widgets_create_new, name='widgets_create_new'),
    url(r'^widgets/edit/(?P<widget_id>[0-9]+)/$', views.widget_edit, name='widget_edit'),
    url(r'^leads/', views.leads, name='leads'),
    url(r'^settings/', views.settings, name='settings'),
    url(r'^billing/', views.billing, name='billing'),
    url(r'^subscribe/(?P<plan_id>[0-9]+)/', views.subscribe, name='subscribe'),
    url(r'^razorpay-webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    url(r'^answer_url/', views.answer_url, name='answer_url'),
    url(r'^call/', views.call, name='call'),

    url(r'^available/', views.call, name='call'),

]
