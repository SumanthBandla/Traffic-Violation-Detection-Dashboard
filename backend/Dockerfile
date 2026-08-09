FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p storage/evidence weights

EXPOSE 8000

CMD ["sh", "-c", "python -m app.scripts.seed_data && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
