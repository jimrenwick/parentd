

from google.appengine.api import users
from google.appengine.ext import ndb
from httplib2 import Http
from oauth2client.appengine import CredentialsModel
from oauth2client.appengine import OAuth2DecoratorFromClientSecrets
from oauth2client.appengine import StorageByKeyName


def GetEndpointsUser():
  user = users.get_current_user()


def EndpointsGetAuthorizedHttp():
  user = users.get_current_user()
  storage = StorageByKeyName(
    CredentialsModel, user.user_id(), 'credentials')
  credentials = storage.get()
  http = Http()
  return credentials.authorize(http)
