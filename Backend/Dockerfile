# Backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN mkdir -p /app/logs
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY . /app/
EXPOSE 8001
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PROMPT_FILE_PATH=/app/app/prompt.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]