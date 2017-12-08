from django.apps import AppConfig


class MainappConfig(AppConfig):
    name = 'mainapp'
    verbose_name = "CallMeNow mainapp"
    def ready(self):
        #Unlock all widgets and set all agents to non-busy
        print("CallMeNow Starting")
