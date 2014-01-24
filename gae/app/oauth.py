# Description:
#   Utilities for authorizing http requests.

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
  user = users.get_current_user()
  return user


def ValidateUser(root_key, needs_super_user=False):
  """Container about how to validate."""
  current_user = GetEndpointsUser()
  # Check that user is allowed in root_key.
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User!')


def IsSuperUser():
  current_user = GetEndpointsUser()
  # if needs_super_user; look up user in allowed, store.
  return True  # for now.


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
