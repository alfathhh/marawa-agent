FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt requirements-operational.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-operational.txt
COPY . .
RUN adduser --system --group --home /app marawa && chown -R marawa:marawa /app
USER marawa

EXPOSE 8080
CMD ["uvicorn", "operational.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
