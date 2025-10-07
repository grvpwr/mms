from django.apps import AppConfig
from .crypto import run_jvm


class MandateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mandate'

    def ready(self):
        run_jvm()