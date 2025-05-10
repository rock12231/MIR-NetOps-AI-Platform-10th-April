# Frontend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
# RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/* # Optional
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY ./src /app/src 
COPY ./data /app/data
EXPOSE 8601
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8601
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
CMD ["streamlit", "run", "src/main.py"]