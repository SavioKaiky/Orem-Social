FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Por padrão instala só as dependências de produção;
# o docker-compose de desenvolvimento passa requirements-dev.txt
ARG REQUIREMENTS_FILE=requirements.txt

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r ${REQUIREMENTS_FILE}

COPY . .

EXPOSE 8000

# Comando de produção (o compose de desenvolvimento sobrescreve)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]