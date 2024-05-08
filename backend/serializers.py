from rest_framework import serializers
from backend.models import Sport, Team, Stadium, Channel, Match, League


class SportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = '__all__'


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'


class StadiumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stadium
        fields = '__all__'


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = '__all__'


class LeagueSerializer(serializers.ModelSerializer):
    class Meta:
        model = League
        fields = '__all__'


class MatchSerializer(serializers.ModelSerializer):
    channels = serializers.PrimaryKeyRelatedField(many=True, queryset=Channel.objects.all())
    home_team_details = serializers.SerializerMethodField()
    visiting_team_details = serializers.SerializerMethodField()
    stadium_details = serializers.SerializerMethodField()
    league_details = serializers.SerializerMethodField()
    sport_details = serializers.SerializerMethodField()
    channels_details = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = '__all__'

    def get_details(self, obj):
        if not obj:
            return {}
        return {
            'id': obj.id,
            'name': obj.name,
            'slug': obj.slug,
            'logo': obj.logo,
        }

    def get_home_team_details(self, obj):
        return self.get_details(obj.home_team)

    def get_visiting_team_details(self, obj):
        return self.get_details(obj.visiting_team)

    def get_stadium_details(self, obj):
        return self.get_details(obj.stadium)

    def get_league_details(self, obj):
        return self.get_details(obj.league)

    def get_sport_details(self, obj):
        return self.get_details(obj.league.sport)

    def get_channels_details(self, obj):
        return [self.get_details(channel) for channel in obj.channels.all()]
