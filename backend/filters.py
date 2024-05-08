from backend.models import *
from backend.constants import *
from django_filters import rest_framework as filters


class MatchFilter(filters.FilterSet):
    flashlive_attrs__STAGE_TYPE = filters.CharFilter(lookup_expr="exact")

    class Meta:
        model = Match
        fields = ['source', 'league']


class LeagueFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    id = filters.BaseInFilter(field_name='id')

    class Meta:
        model = League
        fields = ['id', 'name', 'source', 'sport']


class TeamFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Team
        fields = ['name']


class SportFilter(filters.FilterSet):
    id = filters.BaseInFilter(field_name='id')

    class Meta:
        model = Sport
        fields = ['id']
