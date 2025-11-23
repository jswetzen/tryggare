import os

from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = [host for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host]
CORS_ALLOW_ALL_ORIGINS = True if not CORS_ALLOWED_ORIGINS else False
