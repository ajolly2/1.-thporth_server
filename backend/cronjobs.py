import time
import requests
import traceback
import concurrent.futures
from backend.models import *
from django.db.models import Q
from backend.constants import *
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.utils.text import slugify
from backend.utils import flashlive_api
from datetime import datetime, timedelta


def process_livesport_data(sport_data):
    with transaction.atomic():
        for data in sport_data:
            try:
                # Convert the naive datetime to timezone-aware datetime
                naive_datetime = datetime.strptime(data.get("date"), "%Y-%m-%dT%H:%M:%S.%fZ")
                match_time = timezone.make_aware(naive_datetime, timezone.utc)

                home_team = "TBD"
                if _t := data.get("home_team"):
                    home_team = _t
                visiting_team = "TBD"
                if _t := data.get("visiting_team"):
                    visiting_team = _t

                match = Match.objects.filter(
                    Q(home_team__name__icontains=home_team) | Q(visiting_team__name__icontains=visiting_team)
                ).filter(league__name__icontains=data.get("league"), match_time=match_time).first()

                if not match:
                    # Get or create teams
                    home_team = None
                    if data.get("home_team_slug"):
                        home_team, _ = Team.objects.get_or_create(
                            slug=data.get("home_team_slug"),
                            defaults={"name": data.get("home_team")}
                        )

                    visiting_team = None
                    if data.get("visiting_team_slug"):
                        visiting_team, _ = Team.objects.get_or_create(
                            slug=data.get("visiting_team_slug"),
                            defaults={"name": data.get("visiting_team")}
                        )

                    sport, _ = Sport.objects.update_or_create(
                        slug=data.get("sport_slug"),
                        defaults={"name": data.get("sport")}
                    )

                    # Get or create other related models
                    league = League.objects.filter(name__iexact=data.get("league").lower()).first()
                    if not league:
                        league, _ = League.objects.get_or_create(
                            slug=data.get("league_slug"),
                            defaults={"name": data.get("league"), "sport": sport, "source": "livesportontv"}
                        )

                    stadium = None
                    if data.get("venue"):
                        stadium, _ = Stadium.objects.get_or_create(
                            slug=slugify(data.get("venue")),
                            defaults={"name": data.get("venue")}
                        )

                    # Convert the naive datetime to timezone-aware datetime
                    naive_datetime = datetime.strptime(data.get("date"), "%Y-%m-%dT%H:%M:%S.%fZ")
                    aware_datetime = timezone.make_aware(naive_datetime, timezone.utc)

                    # Create or update Match instance
                    match, _ = Match.objects.update_or_create(
                        slug=data.get("fixture_id"),
                        defaults={
                            "name": data.get("title"),
                            "match_time": aware_datetime,
                            "league": league,
                            "stadium": stadium,
                            "home_team": home_team,
                            "visiting_team": visiting_team,
                            "additional_info": data.get("additional_info"),
                            "livesport_fixture_id": data.get("fixture_id"),
                            "deep_links": data.get("deep_links", []),
                        }
                    )

                # Get or create channels
                channels = [
                    Channel.objects.update_or_create(
                        slug=channel_data.get("url_slug"),
                        defaults={"name": channel_data.get("name"), "url": channel_data.get(
                            "url"), "livesport_channel_id": channel_data.get("id")}
                    )[0] for channel_data in data.get("channels", [])
                ]

                # Add channels to the match
                match.channels.add(*channels)
            except:
                traceback.print_exc()


def livesportsontv_scrapper(request=None):
    # Cron#1
    for sport in SPORTS:
        if sport_slug := sport.get("slug"):
            api_url = LIVESPORTSONTV_API.format(sport_slug=sport_slug)
            try:
                print("=========================================")
                print("Processing Sport:", sport.get("name"))
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    print("Total Records Found:", len(data))
                    process_livesport_data(data)
            except:
                pass
            # Delete unused records.
            current_datetime = datetime.now(tz=timezone.utc)
            two_days_ago = current_datetime - timedelta(days=2)
            Match.objects.filter(match_time__lte=two_days_ago).delete()

    return JsonResponse({"message": "Data scrapped successfully!"})


def process_flashlive_data(tournaments):
    event_attrs = [
        "STAGE", "STAGE_TYPE", "HOME_GOAL_VAR", "HOME_SCORE_CURRENT", "HOME_SCORE_PART_1",
        "HOME_SCORE_PART_2", "HOME_SCORE_PART_3", "HOME_SCORE_PART_4", "WINNER", "AWAY_SCORE_CURRENT",
        "AWAY_SCORE_FULL", "AWAY_SCORE_PART_1", "AWAY_SCORE_PART_2", "AWAY_SCORE_PART_3", "AWAY_SCORE_PART_4",
        "HOME_SCORE_FULL", "AWAY_GOAL_VAR", "HOME_GOAL_VAR", "TV_LIVE_STREAMING", "GAME_TIME", "STAGE_START_TIME"
    ]
    tournaments = tournaments['DATA']

    with transaction.atomic():
        for tournament in tournaments:
            league = League.objects.filter(slug=tournament.get("TOURNAMENT_ID")).first()
            if not league:
                continue

            for event in tournament.get("EVENTS", []):
                naive_datetime = datetime.utcfromtimestamp(event.get("START_UTIME"))
                match_time = timezone.make_aware(naive_datetime, timezone.utc)

                flashlive_attrs = {}
                for attr in event_attrs:
                    if e_attr := event.get(attr):
                        flashlive_attrs[attr] = e_attr

                # Get or create home teams
                home_team = None
                for home_participant_id in event.get("HOME_PARTICIPANT_IDS", []):
                    team_defaults = {"name": event.get("HOME_NAME")}
                    if images := event.get("HOME_IMAGES", []):
                        team_defaults['logo'] = {
                            "src": images[0]
                        }
                    home_team, _ = Team.objects.get_or_create(
                        slug=home_participant_id,
                        defaults=team_defaults
                    )
                    break

                # Get or create visiting teams
                away_team = None
                for away_participant_id in event.get("AWAY_PARTICIPANT_IDS", []):
                    team_defaults = {"name": event.get("AWAY_NAME")}
                    if images := event.get("AWAY_IMAGES", []):
                        team_defaults['logo'] = {
                            "src": images[0]
                        }
                    away_team, _ = Team.objects.get_or_create(
                        slug=away_participant_id,
                        defaults=team_defaults
                    )
                    break

                Match.objects.update_or_create(
                    slug=event.get("EVENT_ID"),
                    defaults={
                        "name": f"{getattr(home_team,'name','TBD')} - {getattr(away_team,'name','TBD')}",
                        "match_time": match_time,
                        "league": league,
                        "home_team": home_team,
                        "visiting_team": away_team,
                        "flashlive_attrs": flashlive_attrs,
                        "source": "flashlive"
                    }
                )


def flashlive_scrapper(request=None):
    # Cron#2
    for sport in SPORTS:
        if sport_id := sport.get('flashlive_id'):
            endpoints = [
                {"endpoint": "events/list", "day_range": range(0, 1)},
                {"endpoint": "events/live-list", "day_range": range(0, 1)}
            ]
            for item in endpoints:
                endpoint, day_range = item.values()
                for day in day_range:
                    try:
                        print("=========================================")
                        print("Processing Sport:", sport.get("name"), ",endpoint:", endpoint, ',day:', day)
                        querystring = {
                            "indent_days": str(day), "timezone": "-4",
                            "locale": "en_INT", "sport_id": sport_id
                        }
                        response = flashlive_api(endpoint, querystring)
                        process_flashlive_data(response)
                    except Exception as e:
                        print(e)

    return JsonResponse({"message": "Data scrapped successfully!"})


def flashlive_process_live_update(sport):
    print("=========================================")
    endpoint = "events/live-update"
    message = f"""Live update: Processing Sport: {sport.get("name")} ,endpoint: {endpoint}"""
    print(message) 
    querystring = {"locale": "en_INT", "sport_id": sport.get('flashlive_id')}

    updates = flashlive_api(endpoint, querystring)

    updates = updates['DATA']
    print("flashlive updates:", updates)
    with transaction.atomic():
        for event in updates:
            if event_id := event.get("EVENT_ID"):
                del event["EVENT_ID"]
                try:
                    match = Match.objects.get(slug=event_id)
                    match.flashlive_attrs.update(event)
                    match.save()
                except:
                    pass


def flashlive_live_updates(request=None):
    # Cron#3
    for i in range(12):
        itr_msg = f"""Iteration# {str(i+1)} starting."""
        print(itr_msg)
        sports = list(filter(lambda x: x.get("flashlive_id"), SPORTS))
        threads = min(len(sports), 4)

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(flashlive_process_live_update, sport): sport for sport in sports}

            for future in concurrent.futures.as_completed(futures):
                sport = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing {sport.get('name')}: {e}")

        print("Iteration#", str(i+1), "completed.")
        time.sleep(2)

    return JsonResponse({"message": "Data updated successfully!"})
