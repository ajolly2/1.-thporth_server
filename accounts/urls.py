from django.urls import path, include
from rest_framework import routers
from accounts.views import UserViewSet
from accounts.views import resetPassword

router = routers.DefaultRouter()
router.register(r'all_users', UserViewSet, basename='all_users')

urlpatterns = [
    path('', include(router.urls)),
    path('reset_password', resetPassword, name='reset_password'),
]
