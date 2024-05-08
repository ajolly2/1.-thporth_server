
from backend.utils import flashlive_api
from backend.models import League, Sport
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def check_name_with_country(self, tournament, query_league_name):
        country = tournament.get("COUNTRY_NAME", "").lower()
        league_name = tournament.get("NAME", "").lower()
        combined_name = f"{country} {league_name}"
        return combined_name == query_league_name

    def handle(self, *args, **options):
        league_names = [line.strip() for line in open('leagues.txt', 'r')]
        for league_name in league_names:
            print("-------------------------------------")
            print("Processing:", league_name)
            querystring = {"query": league_name, "locale": "en_INT"}
            response = flashlive_api("search/multi-search", querystring)
            for tournament in response:
                league_name = league_name.lower()
                if tournament.get("TYPE") == "tournament_templates" and (tournament.get("NAME", "").lower() == league_name or self.check_name_with_country(tournament, league_name)):
                    try:
                        sport = Sport.objects.get(flashlive_id=tournament.get("SPORT_ID"))
                        t_id = tournament.get("TOURNAMENT_ID")
                        League.objects.get_or_create(
                            slug=t_id,
                            defaults={"name": tournament.get("NAME"), "sport": sport, "logo": {
                                "src": tournament.get("IMAGE")
                            }}
                        )
                        print("Tournament added:", t_id)
                    except:
                        pass
