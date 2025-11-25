import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class Family(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_participation_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Participation Date"))

    class Meta:
        db_table = "families"
        verbose_name = _("Family")
        verbose_name_plural = _("Families")

    def __str__(self) -> str:
        return f"Family {self.id}" if not self.parents.exists() else f"{self.parents.first().name}'s family"


class Parent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    phone = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Phone"))
    email = models.EmailField(null=True, blank=True, verbose_name=_("Email"))
    relationship_type = models.CharField(max_length=64, verbose_name=_("Relationship Type"))
    last_participation_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Participation Date"))
    family = models.ForeignKey(Family, related_name="parents", on_delete=models.CASCADE, verbose_name=_("Family"))

    class Meta:
        db_table = "parents"
        verbose_name = _("Parent")
        verbose_name_plural = _("Parents")
        indexes = [
            models.Index(fields=["family"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.relationship_type})"


class Child(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=255, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=255, verbose_name=_("Last Name"))
    birthdate = models.DateField(verbose_name=_("Birthdate"))
    allergies = models.TextField(null=True, blank=True, verbose_name=_("Allergies"))
    notes = models.TextField(null=True, blank=True, verbose_name=_("Notes"))
    qr_token = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name=_("QR Token"))
    last_participation_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Participation Date"))
    family = models.ForeignKey(Family, related_name="children", on_delete=models.CASCADE, verbose_name=_("Family"))

    class Meta:
        db_table = "children"
        verbose_name = _("Child")
        verbose_name_plural = _("Children")
        indexes = [
            models.Index(fields=["qr_token"]),
            models.Index(fields=["last_name"]),
            models.Index(fields=["family"]),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"
