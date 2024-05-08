import json
import math
import boto3
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from collections import defaultdict
from collections import OrderedDict
from rest_framework import viewsets
from django.http import HttpResponse
from datetime import datetime, timedelta
from django.db.models import Prefetch, Min
from djoser.email import PasswordResetEmail
from rest_framework.decorators import action

from PIL import Image
from django.utils.text import slugify
from backend.utils import random_string
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import permission_classes, api_view

from backend.filters import *
from django_filters.rest_framework import DjangoFilterBackend


from backend.models import Sport, Team, Stadium, Channel, Match, League
from backend.serializers import (
    SportSerializer, TeamSerializer, StadiumSerializer, ChannelSerializer, MatchSerializer, LeagueSerializer
)

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.REGION_NAME
)


class THPORTHPagination(PageNumberPagination):
    def get_paginated_response(self, data):
        start_number = self.page.start_index() if self.page.start_index() else 0
        results = [
            {
                **item,
                'sr': start_number + idx
            }
            for idx, item in enumerate(data)
        ]
        return Response({
            'total': self.page.paginator.count,
            'results': results,
            'pageInfo': {
                'hasNextPage': self.page.has_next(),
                'hasPreviousPage': self.page.has_previous()
            }
        })

    def get_page_size(self, request):
        return int(request.query_params.get('perPage', 10))


class PublicListRoutes(viewsets.ModelViewSet):
    """
    Base viewset that makes 'list' route public.
    """

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'list':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]


class THPORTHViewSet(viewsets.ModelViewSet):
    pagination_class = THPORTHPagination

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        return super().perform_create(serializer)

    def get_serializer_context(self):
        if self.request:
            return {'request': self.request}

    def create(self, request, *args, **kwargs):
        if hasattr(self.queryset.model, "slug"):
            passed_slug = request.data.get('slug')
            name = request.data.get('name')
            slug = passed_slug or slugify(name or random_string())

            while self.queryset.model.objects.filter(slug=slug).exists():
                slug = slugify((passed_slug or name) + "-" + random_string())

            request.data['slug'] = slug

        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        try:
            sort = self.request.query_params.get('sort', None)
            if sort is not None:
                queryset = queryset.order_by(sort)
        except:
            pass

        return queryset


class SportViewSet(THPORTHViewSet, PublicListRoutes):
    serializer_class = SportSerializer
    queryset = Sport.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = SportFilter


class TeamViewSet(THPORTHViewSet):
    serializer_class = TeamSerializer
    queryset = Team.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = TeamFilter


class StadiumViewSet(THPORTHViewSet):
    serializer_class = StadiumSerializer
    queryset = Stadium.objects.all()


class ChannelViewSet(THPORTHViewSet):
    serializer_class = ChannelSerializer
    queryset = Channel.objects.all()


class LeagueViewSet(THPORTHViewSet):
    serializer_class = LeagueSerializer
    queryset = League.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = LeagueFilter


class MatchViewSet(THPORTHViewSet):
    serializer_class = MatchSerializer
    queryset = Match.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = MatchFilter

    def get_queryset(self):
        return super().get_queryset().select_related('home_team', 'visiting_team', 'stadium', 'league').prefetch_related('channels')

    @action(
        detail=False, methods=['post'],
        authentication_classes=[TokenAuthentication],
        permission_classes=[IsAuthenticated]
    )
    def matches_batch_update(self, request):
        try:
            data = request.data
            # Remove column name
            data.remove(data[0])
            for row in data:
                try:
                    away = row[0]
                    home = row[1]
                    date = row[3]
                    time = row[4]
                    match_time = datetime.fromisoformat((date.split("T")[0]+"T"+time.split("T")[1])[:-1])
                    league_name = row[5]
                    stream_links = [{'name': "Watch Online", 'url': row[6]}]

                    Match.objects.filter(
                        Q(visiting_team__name__icontains=away, home_team__name__icontains=home) |
                        Q(visiting_team__name__icontains=home, home_team__name__icontains=away),
                        league__name__icontains=league_name,
                        match_time=match_time
                    ).update(stream_links=stream_links)
                except:
                    pass
        except:
            return Response({"success": False})

        return Response({"success": True})


class THPORTHPasswordResetEmail(PasswordResetEmail):
    template_name = "password_reset_email.html"


@permission_classes([IsAuthenticated])
def duplicateData(request):
    error_reponse = HttpResponse(
        json.dumps({"duplicated": False}), content_type='application/json'
    )
    model = request.GET.get("model", None)
    id = request.GET.get("id", None)
    if not model or not id:
        return error_reponse

    if model == "sport":
        model = Sport
    elif model == "team":
        model = Team
    elif model == "stadium":
        model = Stadium
    elif model == "channel":
        model = Channel
    elif model == "sport":
        model = Sport
    elif model == "match":
        model = Match
    else:
        return error_reponse

    try:
        obj = model.objects.get(pk=id)
        obj.pk = None
        obj.save()
    except Exception as e:
        print(e)
        return error_reponse
    return HttpResponse(json.dumps({"duplicated": True}), content_type='application/json')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_image(request):
    try:
        unique_id = "uploads/" + str(random_string(length=32)) + ".png"
        image = request.FILES['image']

        # Compress Image
        image = Image.open(image)
        scale_factor = 0.9
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)
        image = image.resize((new_width, new_height), resample=Image.LANCZOS)
        image = image.convert('RGBA')
        image.save('resized_image.png')

        # Open compressed image and upload
        with open('resized_image.png', 'rb') as data:
            s3_client.upload_fileobj(data, settings.BUCKET_NAME, unique_id)
            download_url = s3_client.generate_presigned_url(
                'get_object', Params={'Bucket': settings.BUCKET_NAME, 'Key': unique_id}
            )
            return Response({'download_url': download_url.split('?', 1)[0], "uploaded": True})
    except Exception as e:
        print(e)
        return Response({"uploaded": False})


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    try:
        if response is not None:
            errors = []
            for field, error_messages in response.data.items():
                errors.append(f"{field.capitalize()}: {' '.join(error_messages)}")
            response.data = '. '.join(errors)
    except:
        response.data = str(response.data)

    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def scheduled_matches(request):
    # Load filters
    filters = request.query_params.get("filters", "{}")
    filters = json.loads(filters)

    # Apply date filters if required
    if filter_date := filters.get("date"):
        match_time = datetime(
            int(filter_date["year"]), int(filter_date["month"]), int(filter_date["date"]),
            tzinfo=timezone.get_current_timezone()
        )
    else:
        match_time = timezone.localtime(timezone.now()).date()

    _Match = Match.objects.filter(match_time__date=match_time)

    # Filter by sport id
    if sport_id := filters.get("sport"):
        _Match = _Match.filter(league__sport=sport_id)

    # Sports
    sports = SportSerializer(Sport.objects.order_by("id").all(), many=True).data
    sports = list(map(
        lambda item: {**item, 'logo': item['logo']['src']} if 'logo' in item and 'src' in item['logo'] else item,
        sports
    ))

    # Get the earliest match time for each league
    earliest_times = _Match.values('league_id').annotate(earliest_time=Min('match_time'))

    # Create a mapping from league_id to its earliest match time
    league_earliest_time = {entry['league_id']: entry['earliest_time'] for entry in earliest_times}

    # Fetch matches and related data
    matches = _Match.order_by('match_time').prefetch_related(
        Prefetch('channels', queryset=Channel.objects.all()),
        Prefetch('home_team', queryset=Team.objects.all()),
        Prefetch('visiting_team', queryset=Team.objects.all()),
        Prefetch('league', queryset=League.objects.all())
    )

    # Group matches under the earliest match time of their league
    matches_grouped = defaultdict(lambda: defaultdict(list))
    for match in matches:
        league_id = match.league.id
        time_key = timezone.localtime(league_earliest_time[league_id]).strftime('%I:%M %p')
        match_data = format_match_detail(match)
        matches_grouped[time_key][league_id].append(match_data)

    # Structure the final response
    scheduled_matches = []
    for time_key, leagues in matches_grouped.items():
        leagues_list = []
        for league_id, matches in leagues.items():
            league = League.objects.get(id=league_id)

            matches.sort(key=lambda x: x['id'])
            last_match_time = None
            for match in matches:
                if last_match_time and last_match_time == match['match_time']['complete_time']:
                    match['match_time'] = None

                if match['match_time']:
                    last_match_time = match['match_time']['complete_time']

            leagues_list.append({
                'id': league.id,
                'name': league.name,
                'matches': matches
            })

        leagues_list.sort(key=lambda x: x['id'])
        scheduled_matches.append({
            'scheduled_time': {
                'complete_time': time_key,
                'time': time_key.split(' ')[0],
                'time_period': time_key.split(' ')[1],
            },
            'leagues': leagues_list
        })

    # Sort response data by scheduled time
    scheduled_matches.sort(key=lambda x: datetime.strptime(x['scheduled_time']['complete_time'], '%I:%M %p'))
    featured_matches = map(format_match_detail, _Match.filter(featured=True).all())

    # Load 10 Dates
    dates = get_top_dates()

    return Response({
        "scheduled_matches": scheduled_matches,
        "featured_matches": featured_matches,
        "sports": sports,
        "dates": dates
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def scheduled_matches_v2(request):
    # Load important leagues and channels
    with open('important_leagues.txt', 'r') as file:
        IMPORTANT_LEAGUES = [line.strip().lower() for line in file]
    with open('important_channels.txt', 'r') as file:
        IMPORTANT_CHANNELS = [line.strip().lower() for line in file]

    # Get today's date
    today = timezone.now().date()

    # Fetch matches for today with related data preloaded
    matches_today = Match.objects.filter(match_time__date=today).prefetch_related(
        Prefetch('channels'),
        Prefetch('home_team'),
        Prefetch('visiting_team'),
        Prefetch('league')
    ).order_by('league__name', 'match_time')

    # Organize matches by league names
    leagues_matches = OrderedDict()
    for match in matches_today:
        league_name = match.league.name
        if league_name not in leagues_matches:
            leagues_matches[league_name] = {
                'league': {'id': match.league.id, 'name': league_name},
                'matches': []
            }

        # Apply format_match_detail to each match and add to the league's list
        if match.flashlive_attrs.get("STAGE_TYPE") != "FINISHED":
            match_data = format_match_detail(match, IMPORTANT_CHANNELS)
            leagues_matches[league_name]['matches'].append(match_data)

            # Check if match is live and update league's is_live flag
            if 'live_text' in match_data:
                leagues_matches[league_name]['league'].setdefault('is_live', False)
                leagues_matches[league_name]['league']['is_live'] = True

    # Convert the ordered dictionary to a structured list
    all_scheduled_matches = list(leagues_matches.values())

    scheduled_matches = []
    low_scheduled_matches = []

    for league_info in all_scheduled_matches:
        if league_info['league']['name'].lower() in IMPORTANT_LEAGUES:
            scheduled_matches.append(league_info)
        else:
            low_scheduled_matches.append(league_info)

    # Sort leagues by their live status
    scheduled_matches = sorted(scheduled_matches, key=lambda x: not x['league'].get('is_live'))
    low_scheduled_matches = sorted(low_scheduled_matches, key=lambda x: not x['league'].get('is_live'))

    return Response({
        "scheduled_matches": scheduled_matches,
        "low_scheduled_matches": low_scheduled_matches,
    })


def format_match_detail(match, IMPORTANT_CHANNELS = []):
    channels = match.channels.all()
    flashlive_attrs = match.flashlive_attrs

    # Update channel url if deeplink found
    for deep_link in match.deep_links:
        for channel in channels:
            if deep_link.get('channel_id') == channel.livesport_channel_id:
                channel.url = deep_link.get('deep_link')
                break

    #
    flash_channels = []
    if match.source == "flashlive":
        flash_channels = [
            {"logo": item["IU"], "name": item["BN"], "url": f"https://www.flashscore.com{item['BU']}"}
            for item in flashlive_attrs.get("TV_LIVE_STREAMING", {}).get("2", []) if "BU" in item
        ]

    all_channels = flash_channels + [
        {'id': channel.id, 'name': channel.name, 'url': channel.url, 'logo': channel.logo.get('src')}
        for channel in channels
    ]

    match_time_local = match.match_time
    match_detail = {
        'id': match.id,
        'match_time': {
            'complete_time': match_time_local,
            'time': match_time_local.strftime('%I:%M'),
            'time_period': match_time_local.strftime('%p'),
        },
        'name': match.name,
        'channels': all_channels,
        'home_team': {'id': match.home_team.id, 'name': match.home_team.name} if match.home_team else None,
        'visiting_team': {'id': match.visiting_team.id, 'name': match.visiting_team.name} if match.visiting_team else None,
        'league_details': {'name': match.league.name},
        'league_name': match.league.name,
        'flashlive_attrs': flashlive_attrs,
        'source': match.source,
        'sport': match.league.sport.name
    }

    if match.stream_links:
        match_detail['channels'][:0] = match.stream_links

    if flashlive_attrs and flashlive_attrs.get("STAGE_TYPE") == "LIVE":
        g_time = flashlive_attrs.get("GAME_TIME")
        if g_time in [-1, "-1", None]:
            try:
                timestamp = flashlive_attrs.get("STAGE_START_TIME")
                match_time_utc = timezone.make_aware(datetime.utcfromtimestamp(timestamp), timezone.utc)
                match_time = timezone.localtime(match_time_utc)
                now_local = timezone.localtime(timezone.now())
                g_time = (now_local - match_time).total_seconds() / 60 + (45 if g_time == None else 0)
                g_time = math.ceil(g_time)
            except:
                pass

        match_detail['live_text'] = f"{g_time}'"

    match_detail['name'] = match_detail['name'].replace(" - ", " vs ")
    if flashlive_attrs.get('AWAY_SCORE_CURRENT') and flashlive_attrs.get('HOME_SCORE_CURRENT'):
        match_detail['name'] = match_detail['name'].replace(" vs ", f" {flashlive_attrs.get('HOME_SCORE_CURRENT')} vs ")
        match_detail['name'] += f" {flashlive_attrs.get('AWAY_SCORE_CURRENT')}"

    for imp_channel in IMPORTANT_CHANNELS:
        for channel in match_detail['channels']:
            if channel.get("name").lower() == imp_channel:
                match_detail['channels'] = [channel]
                return match_detail

    match_detail['channels'] = []
    return match_detail


def get_top_dates():
    today = timezone.localtime(timezone.now())
    # Create a list of 10 formatted dates
    dates = [
        {
            'id': i + 1,
            "date": {
                "date": (today + timedelta(days=i)).strftime("%d"),
                "month": (today + timedelta(days=i)).strftime("%m"),
                "year": (today + timedelta(days=i)).strftime("%Y"),
                "day": "TODAY" if i == 0 else (today + timedelta(days=i)).strftime("%a").upper(),
            },
            "active": i == 0,
        }
        for i in range(10)
    ]

    return dates
