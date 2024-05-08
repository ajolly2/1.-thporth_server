"""
URL configuration for thporth_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from backend.views import duplicateData

from drf_yasg import openapi
from rest_framework import permissions
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title="THPORTH ",
        default_version='v1',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Custom Routes
    path('backend/api/v1/', include("backend.urls")),
    path('backend/duplicate-data/', duplicateData, name='duplicate-data'),
    # Admin Route
    path('backend/admin/', admin.site.urls),
    # Auth Routes
    path("backend/api/v1/", include("accounts.urls")),
    path("backend/api/v1/", include("djoser.urls")),
    path("backend/api/v1/", include("djoser.urls.jwt")),
    path('backend/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path("__debug__/", include("debug_toolbar.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        # Swagger
        path(
            'backend/docs/',
            schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'
        ),
    ]
