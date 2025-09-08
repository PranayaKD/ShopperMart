from django.apps import AppConfig


class ShoppermartappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ShopperMartapp'
    def ready(self):
        import ShopperMartapp.signals  # noqa