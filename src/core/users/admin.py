from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PatientProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (  # type: ignore[operator]
        ('Additional Info', {'fields': ('phone_number',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (  # type: ignore[operator]
        ('Additional Info', {'fields': ('phone_number',)}),
    )


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = (
        'get_full_name',
        'phone_number',
        'blood_group',
        'date_of_birth',
        'registered_at_center',
    )
    search_fields = (
        'user__first_name',
        'user__last_name',
        'user__email',
        'phone_number',
    )
    list_filter = ('blood_group', 'registered_at_center')
    autocomplete_fields = ['user']

    @admin.display(description='Full name')
    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name()
