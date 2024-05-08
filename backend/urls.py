from django.urls import path, include
from rest_framework import routers
from backend.views import (
    SportViewSet, TeamViewSet, StadiumViewSet, ChannelViewSet, MatchViewSet, LeagueViewSet,
    save_image, scheduled_matches, scheduled_matches_v2
)
from backend.cronjobs import livesportsontv_scrapper, flashlive_scrapper, flashlive_live_updates

# Router
router = routers.DefaultRouter()
router.register(r'sports', SportViewSet, basename='sports'),
router.register(r'teams', TeamViewSet, basename='teams'),
router.register(r'stadiums', StadiumViewSet, basename='stadiums'),
router.register(r'channels', ChannelViewSet, basename='channels'),
router.register(r'leagues', LeagueViewSet, basename='leagues'),
router.register(r'matches', MatchViewSet, basename='matches'),

urlpatterns = [
    path('', include(router.urls)),
    path('save-image/', save_image, name='save-image'),
    path('livesportsontv-scrapper/', livesportsontv_scrapper, name='livesportsontv-scrapper'),
    path('flashlive-scrapper/', flashlive_scrapper, name='flashlive-scrapper'),
    path('flashlive-live-updates/', flashlive_live_updates, name='flashlive-live-updates'),
    path('scheduled_matches/', scheduled_matches, name='scheduled_matches'),
    path('scheduled_matches_v2/', scheduled_matches_v2, name='scheduled_matches_v2')
]
