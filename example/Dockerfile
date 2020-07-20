FROM python:3.8.4-alpine

RUN apk add build-base && \
    pip install nameko
COPY service.py /service.py

CMD ["nameko", "run", "service:MyService", "--broker", "pyamqp://guest@rabbitmq:5672"]
