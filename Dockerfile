FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn
COPY main.py .
ARG APP_MESSAGE=Default Message
ENV APP_MESSAGE=$APP_MESSAGE
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
