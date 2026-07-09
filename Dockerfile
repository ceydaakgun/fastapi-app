FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py chatbot.py ./
ARG APP_MESSAGE=Chatbot API is running
ENV APP_MESSAGE=$APP_MESSAGE
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
