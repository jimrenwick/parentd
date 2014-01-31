# Description:
#   Utilities for authorizing http requests.

import endpoints

from google.appengine.api import users
from google.appengine.ext import ndb
from httplib2 import Http
from oauth2client.appengine import CredentialsModel
from oauth2client.appengine import OAuth2DecoratorFromClientSecrets
from oauth2client.appengine import StorageByKeyName


def GetEndpointsUser():
  """Since the endpoints.User doesn't have user_id set, we just use User.

  Returns:
    user: (User) Gets the user struct.
  """
  user = endpoints.get_current_user()
  if not user.user_id():
    user = users.get_current_user()
  return user


def ValidateUser(cls, key):
  """Container about how to validate."""
  current_user = GetEndpointsUser()
  # Check that user is allowed in root_key.
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User!')


def IsSuperUser(user_cls):
  u = user_cls.Find()
  if not u:
    return False
  return u.is_super_user


def EndpointsGetAuthorizedHttp():
  """Sign an Http with user credentials.

  Returns:
    Http: An authorized Http connection.
  """
  user = users.get_current_user()
  storage = StorageByKeyName(
    CredentialsModel, user.user_id(), 'credentials')
  credentials = storage.get()
  http = Http()
  return credentials.authorize(http)
