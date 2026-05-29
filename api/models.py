from django.db import models

# Create your models here.
class Status(models.TextChoices):
    PENDENTE = 'pendente', 'Pendente'
    CONCLUIDO = 'concluido', 'Concluído'


class Tarefa(models.Model):
    payload = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDENTE,
    )

    class Meta:
        db_table = 'tarefas'
