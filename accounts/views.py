
from django.db.models import Q
from accounts.models import User
from django.conf import settings
from rest_framework import viewsets
from django.http import HttpResponse
from django.shortcuts import redirect
from accounts.filters import UserFilter
from accounts.serializers import UserSerializer
from django_filters.rest_framework import DjangoFilterBackend


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().filter(~Q(email="superuser@thporth.com")).order_by("id")
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter


def resetPassword(request):
    uid, token = request.GET.get('uid'), request.GET.get('token')
    if not uid or not token:
        return HttpResponse("Invalid Request.")
    admin_url = settings.ADMIN_FRONTEND_LINK + f"#/change-password?uid={uid}&token={token}"
    return redirect(admin_url)
