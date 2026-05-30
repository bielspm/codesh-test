# Coodesh - desacoplamento de whatsapp e LLM

## Como a solução foi estruturada

O desacoplamento da requisição Http e da resposta da LLM foi feito adicionando uma camada composta de uma fila de tarefas para processamento posterior.

Como funciona ?

Quando a API recebe uma requisição, ela retorna uma resposta rapida, e cria uma tarefa para ser processada posteriormente.
Quando a tarefa é processada, o resultado é retornado para quem a chamou. No nosso caso, o resultado é adiciona em um arquivo de log (app.log) que reside na pasta raiz do projeto.

## Fluxo de processamento

```
POST /hook na API
    │
    ▼
A API responde rapidamente
    |
    |- E cria uma Tarefa para processamento posterior
    │
    ▼
Worker processa (simulação de 30s)
    │
    ├─ Sucesso → o resultado é adicionado ao arquivo de Log
    └─ Falha   → retry (até 3x, backoff 60–180s) → fila de erros
```

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Framework web | Django 5.0 |
| Fila de tarefas | Celery 5.6 |
| Broker / cache | Redis 8 |
| Resultado das tarefas | django-celery-results |
| Gerenciador de processos | Honcho |
| Containerização | Docker + Docker Compose |

## Como rodar o projeto (com Docker)

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado
- [Docker Compose](https://docs.docker.com/compose/install/) instalado (incluso no Docker Desktop)

### Subir o ambiente

```bash
docker compose up --build
```

Isso irá:

1. Construir a imagem da aplicação a partir do `Dockerfile`
2. Subir o container Redis (broker)
3. Executar as migrations do banco de dados
4. Iniciar o servidor Django na porta `8000` e o worker Celery

A aplicação estará disponível em: `http://localhost:8000`

### Parar o ambiente

```bash
docker compose down
```

## Endpoint disponível

### `POST /hook`

Recebe um payload JSON e enfileira para processamento assíncrono.

**Exemplo de requisição:**

```bash
curl -X POST http://localhost:8000/hook \
  -H "Content-Type: application/json" \
  -d '{"payload": "texto aleatorio texto aleatorio"}'
```

**Respostas:**

| Código | Descrição |
|---|---|
| `202 Accepted` | Payload recebido e enfileirado com sucesso |
| `400 Bad Request` | JSON inválido |
| `500 Internal Server Error` | Erro inesperado no servidor |

1. Faça uma requisição, depois abra o arquivo de log (app.log)
2. Verá que um log novo foi criado, mostrando que a requisição foi recebida
3. Espere 30 segundos, e verá um novo log com o resultado do processamento

## Como rodar os testes

Na pasta raiz do projeto:
```bash
py manage.py test
```