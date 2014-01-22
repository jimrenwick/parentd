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
