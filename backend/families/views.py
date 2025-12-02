from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Child, Family, Parent
from .serializers import (
    ChildSerializer,
    FamilyCreateSerializer,
    FamilyDetailSerializer,
    FamilySerializer,
    ParentSerializer,
)


class FamilyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing families.
    Requires authentication for all actions.
    """

    queryset = Family.objects.prefetch_related("parents", "children").all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return FamilyCreateSerializer
        if self.action == "retrieve":
            return FamilyDetailSerializer
        return FamilySerializer

    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        """Get all children for a specific family"""
        family = self.get_object()
        children = family.children.all()
        serializer = ChildSerializer(children, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def parents(self, request, pk=None):
        """Get all parents for a specific family"""
        family = self.get_object()
        parents = family.parents.all()
        serializer = ParentSerializer(parents, many=True)
        return Response(serializer.data)


class ParentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing parents.
    Requires authentication.
    """

    queryset = Parent.objects.select_related("family").all()
    serializer_class = ParentSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "email", "phone"]
    filterset_fields = ["family", "relationship_type"]


class ChildViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing children.
    Requires authentication for most actions.
    """

    queryset = Child.objects.select_related("family").all()
    serializer_class = ChildSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["first_name", "last_name", "qr_token"]
    filterset_fields = ["family"]

    def perform_update(self, serializer):
        """Update last_participation_date when child info is updated"""
        serializer.save(last_participation_date=timezone.now())
