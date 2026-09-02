FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY web ./web
COPY .env.example ./.env.example

RUN mkdir -p /app/data

EXPOSE 8080

CMD ["python", "-m", "app.main"]
