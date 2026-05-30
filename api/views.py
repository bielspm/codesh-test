import base64
import logging
import json

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from api.models import Tarefa, Status
from api.tasks import process_hook

logger = logging.getLogger(__name__)


@require_POST
@csrf_exempt
def hook(request: HttpRequest):
    try:
        json.loads(request.body.decode())  # valida que o corpo é JSON
        encoded_payload = base64.b64encode(request.body).decode()
        tarefa = Tarefa.objects.create(payload=encoded_payload, status=Status.PENDENTE)
        process_hook.delay(tarefa.id)
        logger.info(f'Hook recebido - Task {tarefa.id} gerada')
        return HttpResponse("A solicitação foi recebida e está sendo processada.", status=202)

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        return HttpResponse("Payload inválido - JSON esperado.", status=400)
    except Exception as e:
        logger.error(f"Erro ao processar hook: {str(e)}")
        return HttpResponse("Erro ao processar solicitação.", status=500)
