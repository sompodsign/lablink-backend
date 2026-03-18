from django.apps import AppConfig


class TenantsConfig(AppConfig):
    name = "core.tenants"

    def ready(self) -> None:
        import core.tenants.signals  # noqa: F401
