import base64
import json
import logging
import random
import time

from celery import shared_task

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


@shared_task(bind=True, max_retries=MAX_RETRIES, queue='default')
def process_hook(self, tarefa_id: int):
    from .models import Status, Tarefa

    try:
        tarefa = Tarefa.objects.get(id=tarefa_id, status=Status.PENDENTE)
        payload = json.loads(base64.b64decode(tarefa.payload.encode()).decode())
        logger.info(f'Processando Task {tarefa_id}')
        time.sleep(30)
        logger.info(f'Task {tarefa_id} finalizada. Payload: {payload}')
        tarefa.status = Status.CONCLUIDO
        tarefa.save(update_fields=['status'])
    except Exception as exc:
        if self.request.retries < MAX_RETRIES:
            delay = random.randint(60, 180)
            logger.warning(
                "process_hook failed for tarefa_id=%s (attempt %d/%d), retrying in %ds: %s",
                tarefa_id, self.request.retries + 1, MAX_RETRIES, delay, exc,
            )
            raise self.retry(exc=exc, countdown=delay)

        logger.error(
            "process_hook permanently failed for tarefa_id=%s after %d attempts: %s",
            tarefa_id, MAX_RETRIES, exc,
        )
        process_hook.apply_async(args=[tarefa_id], queue='errors')
