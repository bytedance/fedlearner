import unittest
from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.initial_db import (_insert_or_update_templates, initial_db, migrate_system_variables,
                                              INITIAL_SYSTEM_VARIABLES)
from fedlearner_webconsole.proto.setting_pb2 import SystemVariables
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from testing.no_web_server_test_case import NoWebServerTestCase


class InitialDbTest(NoWebServerTestCase):

    def test_initial_db(self):
        initial_db()
        with db.session_scope() as session:
            self.assertEqual(SettingService(session).get_system_variables_dict()['namespace'], 'default')

    def test_merge_system_variables(self):
        with db.session_scope() as session:
            migrate_system_variables(session, INITIAL_SYSTEM_VARIABLES)
            session.commit()

        with db.session_scope() as session:
            migrate_system_variables(
                session,
                ParseDict(
                    {
                        'variables': [{
                            'name': 'namespace',
                            'value': 'not_default'
                        }, {
                            'name': 'unknown',
                            'value': 'test'
                        }]
                    }, SystemVariables()))
            self.assertEqual(SettingService(session).get_system_variables_dict()['namespace'], 'default')
            self.assertEqual(SettingService(session).get_system_variables_dict()['unknown'], 'test')
            session.commit()

    def test_insert_syspreset_template(self):
        with db.session_scope() as session:
            _insert_or_update_templates(session)
            session.commit()

        with db.session_scope() as session:
            self.assertEqual(session.query(WorkflowTemplate).count(), 18)


if __name__ == '__main__':
    unittest.main()
