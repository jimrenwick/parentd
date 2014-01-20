# Description:
#   Bare-bones, online database with parent/kid contact information.
#   Uses GAE Endpoints to make things simple in the clients.

import endpoints
import logging
import os

from apiclient.discovery import build
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.db import BadArgumentError
from oauth2client.appengine import OAuth2DecoratorFromClientSecrets
from protorpc import messages
from protorpc import message_types
from protorpc import remote

import oauth


U = '884138883203.apps.googleusercontent.com'
ANDROID_AUDIENCE = WEB_CLIENT_ID = U


# Since Google Groups doesn't have an external API, we need a
# different mechanism for managing user permissions. I'll be lazy and
# assume that there is a school administrator....

# District acts like a namespace. We need this so that we have a root
# key for persisting associated classes.
class District(ndb.Expando):
  """The database entry."""
  domain = ndb.StringProperty(required=True)


class DistrictMessage(messages.Message):
  """The endpoints protorpc for a single db record."""
  domain = messages.StringField(1, required=True)


class DistrictCollectionMessage(messages.Message):
  """Used when listing all districts."""
  items = messages.MessageField(DistrictMessage, 1, repeated=True)


# Broker between District formats
def DistrictFromDistrictMessage(pb, **kwargs):
  current_user = oauth.GetEndpointsUser()
  logging.info('District, User = %s' % (current_user))
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User')
  # TODO: Assert in superadmin list.
  v = District.get_by_id(pb.domain)
  if not v:
    v = District(domain=pb.domain, **kwargs)
    v.put()
  return v


def DistrictMessageFromDistrict(obj):
  current_user = oauth.GetEndpointsUser()
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User')
  o = DistrictMessage(domain=obj.key.id())
  return o


def DistrictCollectionMessageFromDistrict(objs):
  container = []
  for o in objs:
    container.append(DistrictMessageFromDistrict(o))
  return DistrictCollectionMessage(items=container)


# Districts have schools. Usually schools are unique within a
# district.
class School(ndb.Expando):
  """The database entry."""
  name = ndb.StringProperty(required=True)
  

class SchoolMessage(messages.Message):
  district = messages.StringField(1, required=True)
  name = messages.StringField(2, required=True)


class SchoolCollectionMessage(messages.Message):
  """Used when listing all districts."""
  items = messages.MessageField(SchoolMessage, 1, repeated=True)


# Broker between School formats
def SchoolFromSchoolMessage(pb, **kwargs):
  current_user = oauth.GetEndpointsUser()
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User')
  d = District.get_by_id(pb.district)
  if not d:
    raise BadArgumentError('No District: %s' % (pb.district))
  v = School.get_by_id(pb.name, parent=d.key)
  if not v:
    v = School(parent=ndb.Key(District, pb.district),
               id=pb.name, name=pb.name, **kwargs)
    v.put()
  return v


def SchoolMessageFromSchool(obj):
  current_user = oauth.GetEndpointsUser()
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User')
  o = SchoolMessage(district=obj.key.id(), name=obj.name)
  return o


def SchoolCollectionMessageFromSchool(objs):
  container = []
  for o in objs:
    container.append(SchoolMessageFromSchool(o))
  return SchoolCollectionMessage(items=container)


# Only some people are allowed into a school.
class Allowed(ndb.Expando):
  emails = ndb.StringProperty(repeated=True)
  

class AllowedMessage(messages.Message):
  district = messages.StringField(1, required=True)
  school = messages.StringField(2, required=True)
  emails = messages.StringField(3, repeated=True)


class AllowedCollectionMessage(messages.Message):
  """Used when listing all districts."""
  items = messages.MessageField(AllowedMessage, 1, repeated=True)


# Broker between Allowed formats
def AllowedFromAllowedMessage(pb, **kwargs):
  current_user = oauth.GetEndpointsUser()
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User')
  d = District.get_by_id(pb.district)
  if not d:
    raise BadArgumentError('No District: %s' % (pb.district))
  s = School.get_by_id(pb.school, parent=d.key)
  if not s:
    raise BadArgumentError('No School: %s' % (pb.school))
  v = Allowed.get_by_id('a', parent=(d.key, s.key))
  if not v:
    v = Allowed(parent=ndb.Key(District, pb.district,
                               School, pb.school),
               id='a', emails=pb.emails, **kwargs)
    v.put()
  return v


def AllowedMessageFromAllowed(obj):
  current_user = oauth.GetEndpointsUser()
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User')
  o = AllowedMessage(district=obj.key.parent.id(),
                     school=obj.key.id(),
                     emails=obj.emails)
  return o


def AllowedCollectionMessageFromAllowed(objs):
  container = []
  for o in objs:
    container.append(AllowedMessageFromAllowed(o))
  return AllowedCollectionMessage(items=container)



# Almost there. People are the people in the school.
class Person(ndb.Model):
  first_name = ndb.StringProperty()
  last_name = ndb.StringProperty()
  phone_number = ndb.StringProperty(repeated=True)
  email_address = ndb.StringProperty(repeated=True)
  address = ndb.StringProperty(repeated=True)


class PersonMessage(messages.Message):
  district = messages.StringField(1, required=True)
  school = messages.StringField(2, required=True)
  first_name = messages.StringField(3)
  last_name = messages.StringField(4)
  phone_number = messages.StringField(5, repeated=True)
  email_address = messages.StringField(6, repeated=True)
  address = messages.StringField(7, repeated=True)


class PersonCollectionMessage(messages.Message):
  """Used when listing all districts."""
  items = messages.MessageField(PersonMessage, 1, repeated=True)


# Broker between Person formats
def PersonFromPersonMessage(pb, **kwargs):
  current_user = oauth.GetEndpointsUser()
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User')
  d = District.get_by_id(pb.district)
  if not d:
    raise BadArgumentError('No District: %s' % (pb.district))
  s = School.get_by_id(pb.school, parent=d.key)
  if not s:
    raise BadArgumentError('No School: %s' % (pb.school))
  v = Person.query(Person.first_name == pb.first_name,
                   Person.last_name == pb.last_name,
                   ancestor=(d.key, s.key))
  if not v:
    v = Person(parent=ndb.Key(District, pb.district,
                               School, pb.school),
               first_name=pb.first_name, last_name=pb.last_name,
               phone_number=pb.phone_number,
               email_address=pb.email_address,
               address=pb.address,
               **kwargs)
    v.put()
  return v


def PersonMessageFromPerson(obj):
  current_user = oauth.GetEndpointsUser()
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User')
  o = PersonMessage(district=obj.key.parent.id(),
                    school=obj.key.id(),
                    first_name=obj.first_name,
                    last_name=obj.last_name,
                    phone_number=obj.phone_number,
                    email_address=obj.email_address,
                    address=obj.address)
  return o


def PersonCollectionMessageFromPerson(objs):
  container = []
  for o in objs:
    container.append(PersonMessageFromPerson(o))
  return PersonCollectionMessage(items=container)


# Finally - A record in the datastore.
class Record(ndb.Expando):
  student = ndb.KeyProperty(kind=Person, required=True)
  grade = ndb.IntegerProperty()
  teacher = ndb.KeyProperty(kind=Person, repeated=True)
  parent = ndb.KeyProperty(kind=Person, repeated=True)
  

class RecordMessage(messages.Message):
  district = messages.StringField(1, required=True)
  school = messages.StringField(2, required=True)
  student = messages.MessageField(PersonMessage, 3, required=True)
  grade = messages.IntegerField(4)
  teacher = messages.MessageField(PersonMessage, 5, repeated=True)
  parent = messages.MessageField(PersonMessage, 6, repeated=True)


class RecordCollectionMessage(messages.Message):
  """Used when listing all districts."""
  items = messages.MessageField(RecordMessage, 1, repeated=True)


# Broker between Record formats
def RecordFromRecordMessage(pb, **kwargs):
  current_user = oauth.GetEndpointsUser()
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User')
  d = District.get_by_id(pb.district)
  if not d:
    raise BadArgumentError('No District: %s' % (pb.district))
  s = School.get_by_id(pb.school, parent=d.key)
  if not s:
    raise BadArgumentError('No School: %s' % (pb.school))
  v = Record.query(
    Record.student.first_name == pb.student.first_name,
    Record.student.last_name == pb.student.last_name,
    ancestor=(d.key, s.key))
  if not v:
    v = Record(parent=ndb.Key(District, pb.district,
                               School, pb.school),
               grade=pb.grade, **kwargs)
    if pb.teacher:
      v.teacher = []
      for t in pb.teacher:
        v.teacher.append(PersonFromPersonMessage(t).key)
    if pb.parent:
      v.parent = []
      for p in pb.parent:
        v.parent.append(PersonFromPersonMessage(p).key)
    v.put()
  return v


def RecordMessageFromRecord(obj):
  current_user = oauth.GetEndpointsUser()
  if not current_user:
    raise endpoints.UnauthorizedException('Invalid User')
  o = RecordMessage(district=obj.key.parent.id(),
                    school=obj.key.id(),
                    grade=obj.grade)
  if obj.teacher:
    l = []
    for t in obj.teacher:
      l.append(PersonMessageFromPerson(t))
    obj.teacher = l
  if obj.parent:
    l = []
    for p in obj.parent:
      l.append(PersonMessageFromPerson(t))
    obj.parent = l
  return o


def RecordCollectionMessageFromRecord(objs):
  container = []
  for o in objs:
    container.append(RecordMessageFromRecord(o))
  return RecordCollectionMessage(items=container)


parentd_api = endpoints.api(
  name='parentd', version='v1.0',
  allowed_client_ids=[WEB_CLIENT_ID, endpoints.API_EXPLORER_CLIENT_ID],
  audiences=[ANDROID_AUDIENCE], scopes=[endpoints.EMAIL_SCOPE])

@parentd_api.api_class(resource_name='district')
class DistrictService(remote.Service):
  @endpoints.method(message_types.VoidMessage, DistrictCollectionMessage,
                    path='district/list', http_method='GET', name='list')
  def DistrictList(self, unused_request):
    q = District.query()
    districts = q.fetch()
    return DistrictCollectionMessageFromDistrict(districts)

  @endpoints.method(DistrictMessage, DistrictMessage,
                    path='district/add', http_method='POST', name='add')
  def DistrictAdd(self, request):
    def _AddTransaction():
      return DistrictFromDistrictMessage(request)
    logging.info('Adding district: %s' % (request))
    obj = ndb.transaction(_AddTransaction, xg=True)
    return DistrictMessageFromDistrict(obj)


@parentd_api.api_class(resource_name='school')
class SchoolService(remote.Service):
  @endpoints.method(message_types.VoidMessage, SchoolCollectionMessage,
                    path='school/list', http_method='GET', name='list')
  def SchoolList(self, unused_request):
    q = School.query()
    schools = q.fetch()
    return SchoolCollectionMessageFromSchool(schools)

  @endpoints.method(SchoolMessage, SchoolMessage,
                    path='school/add', http_method='POST', name='add')
  def SchoolAdd(self, request):
    def _AddTransaction():
      return SchoolFromSchoolMessage(request)
    logging.info('Adding school: %s' % (request))
    obj = ndb.transaction(_AddTransaction, xg=True)
    return SchoolMessageFromSchool(obj)

@parentd_api.api_class(resource_name='allowed')
class AllowedService(remote.Service):
  @endpoints.method(message_types.VoidMessage, AllowedCollectionMessage,
                    path='allowed/list', http_method='GET', name='list')
  def AllowedList(self, unused_request):
    q = Allowed.query()
    alloweds = q.fetch()
    return AllowedCollectionMessageFromAllowed(alloweds)

  @endpoints.method(AllowedMessage, AllowedMessage,
                    path='allowed/add', http_method='POST', name='add')
  def AllowedAdd(self, request):
    def _AddTransaction():
      return AllowedFromAllowedMessage(request)
    logging.info('Adding allowed: %s' % (request))
    obj = ndb.transaction(_AddTransaction, xg=True)
    return AllowedMessageFromAllowed(obj)


@parentd_api.api_class(resource_name='person')
class PersonService(remote.Service):
  @endpoints.method(message_types.VoidMessage, PersonCollectionMessage,
                    path='person/list', http_method='GET', name='list')
  def PersonList(self, unused_request):
    q = Person.query()
    persons = q.fetch()
    return PersonCollectionMessageFromPerson(persons)

  @endpoints.method(PersonMessage, PersonMessage,
                    path='person/add', http_method='POST', name='add')
  def PersonAdd(self, request):
    def _AddTransaction():
      return PersonFromPersonMessage(request)
    logging.info('Adding person: %s' % (request))
    obj = ndb.transaction(_AddTransaction, xg=True)
    return PersonMessageFromPerson(obj)


@parentd_api.api_class(resource_name='record')
class RecordService(remote.Service):
  @endpoints.method(message_types.VoidMessage, RecordCollectionMessage,
                    path='record/list', http_method='GET', name='list')
  def RecordList(self, unused_request):
    q = Record.query()
    records = q.fetch()
    return RecordCollectionMessageFromRecord(records)

  @endpoints.method(RecordMessage, RecordMessage,
                    path='record/add', http_method='POST', name='add')
  def RecordAdd(self, request):
    def _AddTransaction():
      return RecordFromRecordMessage(request)
    logging.info('Adding record: %s' % (request))
    obj = ndb.transaction(_AddTransaction, xg=True)
    return RecordMessageFromRecord(obj)

api = endpoints.api_server([
    DistrictService,
    SchoolService,
    AllowedService,
    PersonService,
    RecordService])


def main():
  logging.getLogger().setLevel(logging.DEBUG)
  webapp.util.run_wsgi_app(APPLICATION)


if __name__ == '__main__':
  main()
