import base64
import json
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from api.models import Status, Tarefa
from api.tasks import MAX_RETRIES, process_hook


# ---------------------------------------------------------------------------
# Unit – Model
# ---------------------------------------------------------------------------

class TarefaModelTest(TestCase):

    def test_default_status_is_pendente(self):
        tarefa = Tarefa.objects.create(payload=base64.b64encode(b'{}').decode())
        self.assertEqual(tarefa.status, Status.PENDENTE)

    def test_status_choices_values(self):
        self.assertEqual(Status.PENDENTE, 'pendente')
        self.assertEqual(Status.CONCLUIDO, 'concluido')

    def test_db_table_name(self):
        self.assertEqual(Tarefa._meta.db_table, 'tarefas')

    def test_payload_is_text_field(self):
        field = Tarefa._meta.get_field('payload')
        self.assertIsNone(field.max_length)


# ---------------------------------------------------------------------------
# Unit – View
# ---------------------------------------------------------------------------

class HookViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('hook')
        self.body = json.dumps({'event': 'push', 'ref': 'main'}).encode()

    @patch('api.views.process_hook', new=MagicMock())
    def test_valid_json_returns_202(self):
        response = self.client.post(self.url, data=self.body, content_type='application/json')
        self.assertEqual(response.status_code, 202)

    @patch('api.views.process_hook', new=MagicMock())
    def test_valid_json_creates_tarefa_with_pendente_status(self):
        self.client.post(self.url, data=self.body, content_type='application/json')
        self.assertEqual(Tarefa.objects.count(), 1)
        self.assertEqual(Tarefa.objects.get().status, Status.PENDENTE)

    @patch('api.views.process_hook', new=MagicMock())
    def test_payload_stored_as_base64_of_raw_body(self):
        self.client.post(self.url, data=self.body, content_type='application/json')
        expected = base64.b64encode(self.body).decode()
        self.assertEqual(Tarefa.objects.get().payload, expected)

    @patch('api.views.process_hook')
    def test_valid_json_dispatches_celery_task(self, mock_task):
        self.client.post(self.url, data=self.body, content_type='application/json')
        tarefa = Tarefa.objects.get()
        mock_task.delay.assert_called_once_with(tarefa.id)

    def test_invalid_json_returns_400(self):
        response = self.client.post(self.url, data='not-json', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_json_creates_no_tarefa(self):
        self.client.post(self.url, data='not-json', content_type='application/json')
        self.assertEqual(Tarefa.objects.count(), 0)

    def test_get_method_returns_405(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_put_method_returns_405(self):
        response = self.client.put(self.url, data=self.body, content_type='application/json')
        self.assertEqual(response.status_code, 405)

    def test_delete_method_returns_405(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 405)


# ---------------------------------------------------------------------------
# Unit – Task
# ---------------------------------------------------------------------------

class ProcessHookTaskTest(TestCase):

    def _create_tarefa(self, status=Status.PENDENTE):
        encoded = base64.b64encode(b'{"event": "test"}').decode()
        return Tarefa.objects.create(payload=encoded, status=status)

    @patch('time.sleep', new=lambda *_: None)
    def test_marks_tarefa_as_concluido(self):
        tarefa = self._create_tarefa()
        process_hook.apply(args=[tarefa.id])
        tarefa.refresh_from_db()
        self.assertEqual(tarefa.status, Status.CONCLUIDO)

    @patch('time.sleep')
    def test_sleeps_30_seconds_during_processing(self, mock_sleep):
        tarefa = self._create_tarefa()
        process_hook.apply(args=[tarefa.id])
        mock_sleep.assert_called_once_with(30)

    @patch('time.sleep', new=lambda *_: None)
    def test_does_not_alter_other_tarefas(self):
        bystander = self._create_tarefa()
        target = self._create_tarefa()
        process_hook.apply(args=[target.id])
        bystander.refresh_from_db()
        self.assertEqual(bystander.status, Status.PENDENTE)

    @patch('api.tasks.process_hook.apply_async')
    @patch('time.sleep', new=lambda *_: None)
    def test_routes_nonexistent_tarefa_to_errors_queue_after_max_retries(self, mock_async):
        process_hook.apply(args=[99999], retries=MAX_RETRIES, throw=False)
        mock_async.assert_called_once_with(args=[99999], queue='errors')

    @patch('api.tasks.process_hook.apply_async')
    @patch('time.sleep', new=lambda *_: None)
    def test_routes_concluido_tarefa_to_errors_queue_after_max_retries(self, mock_async):
        tarefa = self._create_tarefa(status=Status.CONCLUIDO)
        process_hook.apply(args=[tarefa.id], retries=MAX_RETRIES, throw=False)
        mock_async.assert_called_once_with(args=[tarefa.id], queue='errors')

    @patch('time.sleep', new=lambda *_: None)
    def test_retries_before_max_retries_raises_retry(self):
        from celery.exceptions import Retry
        with self.assertRaises(Retry):
            process_hook.apply(args=[99999], retries=0, throw=True)


# ---------------------------------------------------------------------------
# Integration – full webhook flow
# ---------------------------------------------------------------------------

@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class WebhookIntegrationTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('hook')

    @patch('time.sleep', new=lambda *_: None)
    def test_post_creates_and_completes_tarefa(self):
        body = b'{"event": "deploy", "ref": "main"}'
        response = self.client.post(self.url, data=body, content_type='application/json')

        self.assertEqual(response.status_code, 202)
        self.assertEqual(Tarefa.objects.count(), 1)

        tarefa = Tarefa.objects.get()
        self.assertEqual(tarefa.payload, base64.b64encode(body).decode())
        self.assertEqual(tarefa.status, Status.CONCLUIDO)

    @patch('time.sleep', new=lambda *_: None)
    def test_multiple_posts_create_independent_tarefas(self):
        for i in range(3):
            body = json.dumps({'seq': i}).encode()
            self.client.post(self.url, data=body, content_type='application/json')

        self.assertEqual(Tarefa.objects.count(), 3)
        self.assertEqual(Tarefa.objects.filter(status=Status.CONCLUIDO).count(), 3)

    def test_invalid_json_creates_no_tarefa(self):
        response = self.client.post(self.url, data='garbage', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Tarefa.objects.count(), 0)
