from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from core.tenants.models import Doctor, Staff

from .models import PatientProfile, User


class StaffInline(admin.StackedInline):
    model = Staff
    extra = 0
    max_num = 1
    verbose_name = 'Staff role'
    verbose_name_plural = 'Staff role'


class DoctorInline(admin.StackedInline):
    model = Doctor
    extra = 0
    max_num = 1
    verbose_name = 'Doctor profile'
    verbose_name_plural = 'Doctor profile'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'is_staff')
    inlines = [StaffInline, DoctorInline]
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
