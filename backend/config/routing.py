"""
WebSocket URL routing for Django Channels
"""

from django.urls import path
from assistant.consumers import AssistantConsumer
from checkins.consumers import CheckInConsumer

websocket_urlpatterns = [
    path("ws/checkins/", CheckInConsumer.as_asgi()),
    path("ws/assistant/events/<uuid:event_id>/", AssistantConsumer.as_asgi()),
]
