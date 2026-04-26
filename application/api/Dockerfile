FROM python:3.11-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY app.py .

ENV PATH="/opt/venv/bin:$PATH"

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["python", "-u", "app.py"]