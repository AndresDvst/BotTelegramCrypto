FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/crypto_bot

COPY crypto_bot/requirements.txt /app/crypto_bot/requirements.txt
RUN pip install --no-cache-dir -r /app/crypto_bot/requirements.txt

COPY crypto_bot/ /app/crypto_bot/

EXPOSE 5000

CMD ["python", "main.py"]
