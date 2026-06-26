from django.contrib import admin

from .models import Child, Family, Parent


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("id", "last_name", "last_participation_date")
    search_fields = ("id", "last_name")
    list_filter = ("last_participation_date",)


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("name", "relationship_type", "family", "phone_locked", "email_locked")
    search_fields = ("name", "email", "phone")
    list_filter = ("relationship_type", "phone_locked", "email_locked")


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "family", "birthdate")
    search_fields = ("first_name", "last_name")
    list_filter = ("last_participation_date",)
