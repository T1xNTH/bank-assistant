FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
# CPU PyTorch wheels are large; tolerate slow first-clone downloads without changing dependencies.
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt
COPY src/ src/
ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
