from django.apps import AppConfig

def ready(self):
    import beacon.signals

class BeaconConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'beacon'
