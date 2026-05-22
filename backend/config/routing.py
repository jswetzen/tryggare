"""
WebSocket URL routing for Django Channels
"""

from django.urls import path
from checkins.consumers import CheckInConsumer

websocket_urlpatterns = [
    path("ws/checkins/", CheckInConsumer.as_asgi()),
]
