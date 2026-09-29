FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
ENV APP_ENV=production
ENV HOST=127.0.0.1

EXPOSE ${PORT}

CMD ["python", "main.py"]
