# ── new-app-starter/Dockerfile ────────────────────────────────────────────────
#
# Layered build pattern:
#   1. Pull flask-app-template from GitHub at build time
#   2. Install template base requirements
#   3. Install app-specific requirements
#   4. Copy template files into /app
#   5. Copy app-specific files into /app (overrides template where names match)
#
# To pin to a specific template version rather than always using latest main:
#   docker-compose build --build-arg TEMPLATE_REF=v1.0
#
# PLACEHOLDER: Replace APP_NAME (myapp) throughout this file.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

WORKDIR /app

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
        gcc \
        curl \
        git \
        nfs-common \
    && rm -rf /var/lib/apt/lists/*

# ── Pull template from GitHub ─────────────────────────────────────────────────
ARG TEMPLATE_REF=main
RUN git clone --depth 1 --branch ${TEMPLATE_REF} \
    https://github.com/kylebrothers/flask-app-template /tmp/template \
    && echo "Template ref: ${TEMPLATE_REF}" \
    && ls /tmp/template

# ── Install template base requirements ───────────────────────────────────────
RUN pip install --no-cache-dir -r /tmp/template/requirements.txt

# ── Install app-specific requirements ────────────────────────────────────────
# Add packages to app/requirements.txt (e.g. python-docx, PyPDF2, requests)
COPY app/requirements.txt ./app-requirements.txt
RUN pip install --no-cache-dir -r app-requirements.txt

# ── Copy template layer ───────────────────────────────────────────────────────
RUN cp -r /tmp/template/. . \
    && rm -rf /tmp/template

# ── Copy app layer (overrides template where names match) ─────────────────────
COPY app/ .

# ── Runtime directories ───────────────────────────────────────────────────────
# These are overridden by NAS volume mounts at runtime.
# The mkdir ensures the container starts cleanly even without mounts.
RUN mkdir -p logs server_files static

# ── Health check ──────────────────────────────────────────────────────────────
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────────
CMD ["python", "app.py"]
