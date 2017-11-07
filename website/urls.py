from django.conf.urls import url, include
from django.contrib.auth import views as auth_views
from . import views

#For namespacing the urls in this app.
app_name = 'website'

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^about-us/', views.about_us, name='about-us'),
    url(r'^faq/', views.faq, name='faq'),
    url(r'^contact-us/', views.contact_us, name='contact-us'),
    url(r'^pricing/', views.pricing, name='pricing'),
]
