# o365pop LibreELEC image — Python 3.14, host-network daemons (DEP1.1).
FROM python:3.14-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY o365pop o365pop
COPY Makefile .

ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "o365pop", "status"]
