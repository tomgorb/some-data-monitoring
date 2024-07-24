FROM python:3.8-slim

ENV PROJECT_NAME=some-data-monitoring

WORKDIR /opt/$PROJECT_NAME

COPY src src

RUN pip install --no-cache-dir --upgrade -r src/requirements.txt
