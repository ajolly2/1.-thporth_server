import django_filters
from accounts.models import User
from accounts.constants import *


class UserFilter(django_filters.FilterSet):
    role = django_filters.ChoiceFilter(choices=USER_ROLES)
    id = django_filters.BaseInFilter(field_name="id")

    class Meta:
        model = User
        fields = ['role', 'id']
