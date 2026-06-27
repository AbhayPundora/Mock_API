FROM python:3.11-slim

WORKDIR /app

# install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy source
COPY . .

EXPOSE 8000

CMD ["python", "-m", "src.seed"]
