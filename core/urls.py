from django.urls import path

from . import flutter, views

urlpatterns = [
    path("", flutter.home, name="home"),
    path("app/", flutter.app, name="flutter-app"),
    path("app/<path:asset_path>", flutter.app, name="flutter-asset"),
    path("manifest.webmanifest", views.manifest, name="pwa-manifest"),
    path("service-worker.js", views.service_worker, name="pwa-service-worker"),
    path("offline/", views.offline, name="pwa-offline"),
    path("install/", views.install, name="pwa-install"),
]
