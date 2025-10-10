from django.apps import AppConfig

class MandateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mandate'

    def ready(self):
        pass