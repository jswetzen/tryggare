from django.contrib import admin

from .models import Child, Family, Parent


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("id", "last_participation_date")
    search_fields = ("id",)


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("name", "relationship_type", "family")
    search_fields = ("name", "email", "phone")
    list_filter = ("relationship_type",)


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "family", "qr_token")
    search_fields = ("first_name", "last_name", "qr_token")
    list_filter = ("last_participation_date",)
