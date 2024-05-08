from django.db import models
from accounts.models import User
from django.conf import settings

# Create your models here.


class THPORTHModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        abstract = True
        ordering = ["-id"]

    def save(self, *args, **kwargs):
        if hasattr(self, "logo") and not self.logo.get("src", None):
            default_logo = self.__class__.__name__.lower() + ".png"
            self.logo = {"src": settings.BUCKET_URL + default_logo, "title": default_logo}

        super().save(*args, **kwargs)


class CommonModelFields(models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200, unique=True)
    logo = models.JSONField(default=dict)

    class Meta:
        abstract = True


class Sport(THPORTHModel, CommonModelFields):
    flashlive_id = models.IntegerField(null=True)


class Team(THPORTHModel, CommonModelFields):
    pass


class Stadium(THPORTHModel, CommonModelFields):
    pass


class Channel(THPORTHModel, CommonModelFields):
    livesport_channel_id = models.IntegerField(null=True)
    url = models.CharField(max_length=1000, null=True,  blank=True)


class League(THPORTHModel, CommonModelFields):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
    source = models.CharField(max_length=200, default="flashlive")


class Match(THPORTHModel):
    match_time = models.DateTimeField()
    name = models.CharField(max_length=200)
    channels = models.ManyToManyField(Channel)
    deep_links = models.JSONField(default=list)
    stream_links = models.JSONField(default=list)
    featured = models.BooleanField(default=False)
    flashlive_attrs = models.JSONField(default=dict)
    slug = models.CharField(max_length=200, unique=True)
    livesport_fixture_id = models.IntegerField(null=True)
    additional_info = models.CharField(max_length=200, null=True)
    source = models.CharField(max_length=200, default="livesport")
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    stadium = models.ForeignKey(Stadium, null=True, on_delete=models.CASCADE)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_team", null=True)
    visiting_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="visiting_team", null=True)
