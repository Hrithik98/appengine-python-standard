#!/usr/bin/env python
#
# Copyright 2007 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Tests for google.appengine.api.modules."""

import os

from google.appengine.api.modules import modules
from google.appengine.runtime.context import ctx_test_util
import mox

from absl.testing import absltest
from googleapiclient import errors


@ctx_test_util.isolated_context()
class ModulesTest(absltest.TestCase):

  def setUp(self):
    """Setup testing environment."""
    self.mox = mox.Mox()
    self.mock_admin_api_client = self.mox.CreateMockAnything()
    self.mox.StubOutWithMock(modules, 'discovery')

    # Environment variables are cleared in tearDown
    os.environ['GAE_APPLICATION'] = 's~project'
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'project'
    os.environ['GAE_SERVICE'] = 'default'
    os.environ['GAE_VERSION'] = 'v1'
    os.environ['CURRENT_MODULE_ID'] = 'default'
    os.environ['CURRENT_VERSION_ID'] = 'v1.123'

  def tearDown(self):
    """Tear down testing environment."""
    self.mox.UnsetStubs()
    self.mox.VerifyAll()

    # Clear environment variables that were set in tests
    for var in [
        'GAE_SERVICE', 'GAE_VERSION', 'CURRENT_MODULE_ID', 'CURRENT_VERSION_ID',
        'INSTANCE_ID', 'GAE_INSTANCE', 'GOOGLE_CLOUD_PROJECT', 'GAE_APPLICATION'
    ]:
      if var in os.environ:
        del os.environ[var]

  def _SetupAdminApiMocks(self, project='project'):
    modules.discovery.build('appengine',
                            'v1').AndReturn(self.mock_admin_api_client)

  def _CreateHttpError(self, status, reason='Error'):
    resp = self.mox.CreateMockAnything()
    resp.status = status
    resp.reason = reason
    return errors.HttpError(resp, b'')

  # --- Tests for Get/Set Current Module, Version, Instance ---

  def testGetCurrentModuleName(self):
    os.environ['GAE_SERVICE'] = 'module1'
    self.assertEqual('module1', modules.get_current_module_name())

  def testGetCurrentModuleName_Fallback(self):
    if 'GAE_SERVICE' in os.environ:
      del os.environ['GAE_SERVICE']
    os.environ['CURRENT_MODULE_ID'] = 'module2'
    self.assertEqual('module2', modules.get_current_module_name())

  def testGetCurrentVersionName(self):
    os.environ['GAE_VERSION'] = 'v2'
    self.assertEqual('v2', modules.get_current_version_name())

  def testGetCurrentVersionName_Fallback(self):
    if 'GAE_VERSION' in os.environ:
      del os.environ['GAE_VERSION']
    os.environ['CURRENT_VERSION_ID'] = 'v3.456'
    self.assertEqual('v3', modules.get_current_version_name())

  def testGetCurrentVersionName_None(self):
    if 'GAE_VERSION' in os.environ:
      del os.environ['GAE_VERSION']
    os.environ['CURRENT_VERSION_ID'] = 'None.456'
    self.assertIsNone(modules.get_current_version_name())

  def testGetCurrentInstanceId(self):
    os.environ['GAE_INSTANCE'] = 'instance1'
    self.assertEqual('instance1', modules.get_current_instance_id())

  def testGetCurrentInstanceId_Fallback(self):
    if 'GAE_INSTANCE' in os.environ:
        del os.environ['GAE_INSTANCE']
    os.environ['INSTANCE_ID'] = 'instance2'
    self.assertEqual('instance2', modules.get_current_instance_id())

  def testGetCurrentInstanceId_None(self):
    if 'GAE_INSTANCE' in os.environ:
      del os.environ['GAE_INSTANCE']
    if 'INSTANCE_ID' in os.environ:
      del os.environ['INSTANCE_ID']
    self.assertIsNone(modules.get_current_instance_id())

  # --- Tests for get_modules ---

  def testGetModules(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.list(appsId='project').AndReturn(mock_request)
    mock_request.execute().AndReturn(
        {'services': [{'id': 'module1'}, {'id': 'default'}]})
    self.mox.ReplayAll()
    self.assertEqual(['module1', 'default'], modules.get_modules())

  def testGetModules_InvalidProject(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.list(appsId='project').AndReturn(mock_request)
    mock_request.execute().AndRaise(self._CreateHttpError(404))
    self.mox.ReplayAll()
    with self.assertRaisesRegex(modules.Error, "Project 'project' not found."):
      modules.get_modules()

  # --- Tests for get_versions ---

  def testGetVersions(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.list(
        appsId='project', servicesId='default', view='FULL').AndReturn(
            mock_request)
    mock_request.execute().AndReturn({'versions': [{'id': 'v1'}, {'id': 'v2'}]})
    self.mox.ReplayAll()
    self.assertEqual(['v1', 'v2'], modules.get_versions())

  def testGetVersions_InvalidModule(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.list(
        appsId='project', servicesId='foo', view='FULL').AndReturn(mock_request)
    mock_request.execute().AndRaise(self._CreateHttpError(404))
    self.mox.ReplayAll()
    with self.assertRaisesRegex(modules.InvalidModuleError,
                                  "Module 'foo' not found."):
      modules.get_versions(module='foo')

  # --- Tests for get_default_version ---

  def testGetDefaultVersion(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.get(appsId='project',
                      servicesId='default').AndReturn(mock_request)
    mock_request.execute().AndReturn(
        {'split': {'allocations': {'v1': 0.5, 'v2': 0.5}}})
    self.mox.ReplayAll()
    self.assertEqual('v1', modules.get_default_version())

  def testGetDefaultVersion_Lexicographical(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.get(appsId='project',
                      servicesId='default').AndReturn(mock_request)
    mock_request.execute().AndReturn(
        {'split': {'allocations': {'v2-beta': 0.5, 'v1-stable': 0.5}}})
    self.mox.ReplayAll()
    self.assertEqual('v1-stable', modules.get_default_version())

  def testGetDefaultVersion_NoDefaultVersion(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.get(appsId='project',
                      servicesId='default').AndReturn(mock_request)
    mock_request.execute().AndReturn({})  # No split allocations
    self.mox.ReplayAll()
    with self.assertRaisesRegex(modules.InvalidVersionError,
                                  'Could not determine default version'):
      modules.get_default_version()

  def testGetDefaultVersion_InvalidModule(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.get(appsId='project',
                      servicesId='foo').AndReturn(mock_request)
    mock_request.execute().AndRaise(self._CreateHttpError(404))
    self.mox.ReplayAll()
    with self.assertRaisesRegex(modules.InvalidModuleError,
                                  "Module 'foo' not found."):
      modules.get_default_version(module='foo')

  # --- Tests for get_num_instances ---

  def testGetNumInstances(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.get(appsId='project', servicesId='default',
                      versionsId='v1').AndReturn(mock_request)
    mock_request.execute().AndReturn({'manualScaling': {'instances': 5}})
    self.mox.ReplayAll()
    self.assertEqual(5, modules.get_num_instances())

  def testGetNumInstances_NoManualScaling(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.get(appsId='project', servicesId='default',
                      versionsId='v1').AndReturn(mock_request)
    mock_request.execute().AndReturn({'automaticScaling': {}})
    self.mox.ReplayAll()
    self.assertEqual(0, modules.get_num_instances())

  def testGetNumInstances_InvalidVersion(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.get(appsId='project', servicesId='default',
                      versionsId='v-bad').AndReturn(mock_request)
    mock_request.execute().AndRaise(self._CreateHttpError(404))
    self.mox.ReplayAll()
    with self.assertRaises(modules.InvalidVersionError):
      modules.get_num_instances(version='v-bad')

  # --- Tests for async operations (set_num_instances, start/stop_version) ---

  def testSetNumInstances(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.patch(
        appsId='project',
        servicesId='default',
        versionsId='v1',
        updateMask='manualScaling.instances',
        body={'manualScaling': {'instances': 10}}).AndReturn(mock_request)
    mock_request.execute()
    self.mox.ReplayAll()
    modules.set_num_instances(10)

  def testSetNumInstances_TypeError(self):
    with self.assertRaises(TypeError):
      modules.set_num_instances('not-an-int')

  def testSetNumInstances_InvalidInstancesError(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.patch(
        appsId='project',
        servicesId='default',
        versionsId='v1',
        updateMask='manualScaling.instances',
        body={'manualScaling': {'instances': -1}}).AndReturn(mock_request)
    mock_request.execute().AndRaise(self._CreateHttpError(400))
    self.mox.ReplayAll()
    with self.assertRaises(modules.InvalidInstancesError):
      modules.set_num_instances(-1)

  def testStartVersion(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.patch(
        appsId='project',
        servicesId='default',
        versionsId='v1',
        updateMask='servingStatus',
        body={'servingStatus': 'SERVING'}).AndReturn(mock_request)
    mock_request.execute()
    self.mox.ReplayAll()
    modules.start_version('default', 'v1')

  def testStartVersion_InvalidVersion(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.patch(
        appsId='project',
        servicesId='default',
        versionsId='v-bad',
        updateMask='servingStatus',
        body={'servingStatus': 'SERVING'}).AndReturn(mock_request)
    mock_request.execute().AndRaise(self._CreateHttpError(404))
    self.mox.ReplayAll()
    with self.assertRaises(modules.InvalidVersionError):
      modules.start_version('default', 'v-bad')

  def testStartVersionAsync_NoneArgs(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.patch(
        appsId='project',
        servicesId='default',
        versionsId='v1',
        updateMask='servingStatus',
        body={'servingStatus': 'SERVING'}).AndReturn(mock_request)
    mock_request.execute()
    self.mox.ReplayAll()
    rpc = modules.start_version_async(None, None)
    rpc.get_result()

  def testStopVersion(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.patch(
        appsId='project',
        servicesId='default',
        versionsId='v1',
        updateMask='servingStatus',
        body={'servingStatus': 'STOPPED'}).AndReturn(mock_request)
    mock_request.execute()
    self.mox.ReplayAll()
    modules.stop_version()

  def testStopVersion_InvalidVersion(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.patch(
        appsId='project',
        servicesId='default',
        versionsId='v-bad',
        updateMask='servingStatus',
        body={'servingStatus': 'STOPPED'}).AndReturn(mock_request)
    mock_request.execute().AndRaise(self._CreateHttpError(404))
    self.mox.ReplayAll()
    with self.assertRaises(modules.InvalidVersionError):
      modules.stop_version(version='v-bad')

  def testStopVersion_TransientError(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.patch(
        appsId='project',
        servicesId='default',
        versionsId='v1',
        updateMask='servingStatus',
        body={'servingStatus': 'STOPPED'}).AndReturn(mock_request)
    mock_request.execute().AndRaise(self._CreateHttpError(500))
    self.mox.ReplayAll()
    with self.assertRaises(modules.TransientError):
      modules.stop_version()

  def testRaiseError_Generic(self):
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_services = self.mox.CreateMockAnything()
    mock_versions = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.services().AndReturn(mock_services)
    mock_services.versions().AndReturn(mock_versions)
    mock_versions.patch(
        appsId='project',
        servicesId='default',
        versionsId='v1',
        updateMask='servingStatus',
        body={'servingStatus': 'STOPPED'}).AndReturn(mock_request)
    mock_request.execute().AndRaise(self._CreateHttpError(401)) # Unauthorized
    self.mox.ReplayAll()
    with self.assertRaises(modules.Error):
        modules.stop_version()

  # --- Tests for get_hostname (intentionally left incomplete) ---

  def testGetHostname(self):
    # This test verifies the current non-error-handled behavior of get_hostname
    self._SetupAdminApiMocks()
    mock_apps = self.mox.CreateMockAnything()
    mock_request = self.mox.CreateMockAnything()
    self.mock_admin_api_client.apps().AndReturn(mock_apps)
    mock_apps.get(appsId='project').AndReturn(mock_request)
    mock_request.execute().AndReturn(
        {'defaultHostname': 'project.appspot.com'})
    self.mox.ReplayAll()
    self.assertEqual('i.v1.default.project.appspot.com',
                     modules.get_hostname(instance='i'))


if __name__ == '__main__':
  absltest.main()

