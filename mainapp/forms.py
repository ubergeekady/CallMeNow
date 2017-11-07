from django import forms

class WidgetForm(forms.Form):
    name = forms.CharField(max_length=30, label='Your name')
    call_setting = forms.CharField(max_length=30, label='Your name')
    call_algorithm = forms.CharField(max_length=30, label='Your name')
    capture_leads = forms.BooleanField(required=False)
    show_on_mobile = forms.BooleanField(required=False)