
from backend.models import Sport
from backend.constants import SPORTS
from backend.utils import random_string
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        for _sport in SPORTS:
            try:
                sport = Sport()
                sport.name = _sport.get("name")
                print("Processing:", _sport.get("name"))
                if slug := _sport.get("slug"):
                    sport.slug = slug
                else:
                    sport.slug = random_string(10).lower()
                sport.flashlive_id = _sport.get("flashlive_id")
                sport.save()
            except:
                pass
