# Description:
#   Endpoints interface for the parentd app.

import endpoints
import logging

from apiclient.discovery import build
from google.appengine.api import users
# from protorpc import messages
# from protorpc import message_types
# from protorpc import remote

import datamodel_lib

# TODO(renwick): Might need to pass around district for all commands.

U = '884138883203.apps.googleusercontent.com'
ANDROID_AUDIENCE = WEB_CLIENT_ID = U

parentd_api = endpoints.api(
  name='parentd', version='v1.0',
  allowed_client_ids=[WEB_CLIENT_ID, endpoints.API_EXPLORER_CLIENT_ID],
  audiences=[ANDROID_AUDIENCE], scopes=[endpoints.EMAIL_SCOPE])

@parentd_api.api_class(resource_name='district')
class DistrictService(remote.Service):
  @endpoints.method(message_types.VoidMessage,
                    datamodel_lib.DistrictCollectionMessage,
                    path='district/list', http_method='GET', name='list')
  def DistrictList(self, unused_request):
    q = datamodel_lib.District.All()
    districts = q.fetch()
    return DistrictCollectionMessageFromDistrict(districts)

  @endpoints.method(datamodel_lib.DistrictMessage, datamodel_lib.DistrictMessage,
                    path='district/add', http_method='POST', name='add')
  def DistrictAdd(self, request):
    def _AddTransaction():
      return datamodel_lib.District.FromMessage(request)
    logging.info('Adding district: %s' % (request))
    obj = ndb.transaction(_AddTransaction, xg=True)
    return datamodel_lib.District.ToMessage(obj)


@parentd_api.api_class(resource_name='school')
class SchoolService(remote.Service):
  @endpoints.method(message_types.VoidMessage,
                    datamodel_lib.SchoolCollectionMessage,
                    path='school/list', http_method='GET', name='list')
  def SchoolList(self, unused_request):
    q = datamodel_lib.School.All()
    schools = q.fetch()
    return SchoolCollectionMessageFromSchool(schools)

  @endpoints.method(datamodel_lib.SchoolMessage,
                    datamodel_lib.SchoolMessage,
                    path='school/add', http_method='POST', name='add')
  def SchoolAdd(self, request):
    def _AddTransaction():
      return datamodel_lib.School.FromMessage(request)
    logging.info('Adding school: %s' % (request))
    obj = ndb.transaction(_AddTransaction, xg=True)
    return datamodel_lib.School.ToMessage(obj)


@parentd_api.api_class(resource_name='record')
class RecordService(remote.Service):
  RecordListResource = endpoints.ResourceContainer(
    message_types.VoidMessage,
    district=messages.StringField(1, required=True),
    school=messages.StringField(1, required=True))
    
  @endpoints.method(RecordListResource,
                    datamodel_lib.RecordCollectionMessage,
                    path='record/list/{district}/{school}',
                    http_method='GET', name='list')
  def RecordList(self, request):
    # Assert the school exists.
    school = datamodel_lib.School.FromMessage(
      datamodel_lib.SchoolMessage(
        district=request.district, name=request.school))
    if not school:
      raise endpoints.NotFoundException('School/District are invalid')
    q = datamodel_lib.Record.All(request.school)
    records = q.fetch()
    return RecordCollectionMessageFromRecord(records)

  @endpoints.method(datamodel_lib.RecordMessage,
                    datamodel_lib.RecordMessage,
                    path='record/add', http_method='POST', name='add')
  def RecordAdd(self, request):
    def _AddTransaction():
      return datamodel_lib.Record.FromMessage(request)
    logging.info('Adding record: %s' % (request))
    obj = ndb.transaction(_AddTransaction, xg=True)
    return datamodel_lib.Record.ToMessage(obj)


# TODO(renwick): Add in the UserService
api = endpoints.api_server([
    DistrictService,
    SchoolService,
    RecordService])
