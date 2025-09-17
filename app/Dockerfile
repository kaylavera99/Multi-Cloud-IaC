FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    CLOUD=local
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m  pip install --no-cache-dir -r requirements.txt
COPY app.py /app/app.py

EXPOSE 8080
CMD ["python", "app.py"]
