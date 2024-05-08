
from backend.models import *
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        Sport.objects.all().delete()
        League.objects.all().delete()
        Stadium.objects.all().delete()
        Team.objects.all().delete()
        Channel.objects.all().delete()
        Match.objects.all().delete()
