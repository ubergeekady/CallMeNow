from django.shortcuts import render

from django.shortcuts import render, get_object_or_404
#from .models import Album,Song
from django.views import generic

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django import forms
#from .forms import UserRegistrationForm

from django.http import HttpResponse

def index(request):
    return render(request, 'website/index.html')

def about_us(request):
    return render(request, 'website/about-us.html')

def faq(request):
    return render(request, 'website/faq.html')

def contact_us(request):
    return render(request, 'website/contact-us.html')

def pricing(request):
    return render(request, 'website/pricing.html')