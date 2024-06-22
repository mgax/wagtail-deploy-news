from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field: str = "django.db.models.AutoField"
    name = "news.users"
    label = "users"
