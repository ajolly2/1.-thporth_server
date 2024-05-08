import string
import random
import requests
from retry import retry
from django.conf import settings
from accounts.constants import SUPER_USER_ROLES


def is_admin(role):
    return role in SUPER_USER_ROLES


def random_string(length=10):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


@retry(Exception, tries=5, delay=1)
def flashlive_api(endpoint, querystring={}):
    fashlive_api = "https://flashlive-sports.p.rapidapi.com/v1/" + endpoint
    headers = {
        "X-RapidAPI-Key": settings.X_RAPIDAPI_KEY,
        "X-RapidAPI-Host": "flashlive-sports.p.rapidapi.com"
    }
    response = requests.get(fashlive_api, headers=headers, params=querystring)
    if response.ok:
        return response.json()
    else:
        print("Error:", response.json())
        raise Exception("API ERROR", response.json())
