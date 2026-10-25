FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ADRESPLAN_DB=/data/adresplan.sqlite3
WORKDIR /app
COPY pyproject.toml README.md LICENSE requirements-dev.lock ./
COPY src ./src
RUN python -m pip install --no-cache-dir -c requirements-dev.lock . \
    && useradd --uid 10001 --create-home app \
    && mkdir /data && chown app:app /data
USER app
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/', timeout=3)"
CMD ["adresplan", "serve", "--host", "0.0.0.0"]
