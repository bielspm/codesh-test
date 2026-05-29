FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIPENV_VENV_IN_PROJECT=1

WORKDIR /app

RUN pip install --no-cache-dir pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv sync --system

COPY . .

RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
