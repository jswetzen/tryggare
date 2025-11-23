import uuid

from django.db import models


class Family(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_participation_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "families"

    def __str__(self) -> str:
        return f"Family {self.id}" if not self.parents.exists() else f"{self.parents.first().name}'s family"


class Parent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    relationship_type = models.CharField(max_length=64)
    last_participation_date = models.DateTimeField(null=True, blank=True)
    family = models.ForeignKey(Family, related_name="parents", on_delete=models.CASCADE)

    class Meta:
        db_table = "parents"
        indexes = [
            models.Index(fields=["family"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.relationship_type})"


class Child(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    birthdate = models.DateField()
    allergies = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    qr_token = models.CharField(max_length=255, unique=True, null=True, blank=True)
    last_participation_date = models.DateTimeField(null=True, blank=True)
    family = models.ForeignKey(Family, related_name="children", on_delete=models.CASCADE)

    class Meta:
        db_table = "children"
        indexes = [
            models.Index(fields=["qr_token"]),
            models.Index(fields=["last_name"]),
            models.Index(fields=["family"]),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"
