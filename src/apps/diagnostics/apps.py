from django.apps import AppConfig


class DiagnosticsConfig(AppConfig):
    name = "apps.diagnostics"

    def ready(self):
        import apps.diagnostics.signals  # noqa: F401
