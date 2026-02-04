# Stage 1: Orbis Toolchain
FROM openorbisofficial/toolchain:latest AS toolchain

# Stage 2: Python 3.12 Runtime
FROM python:3.12-slim

RUN python -m pip install --no-cache-dir requests

# Stage 3: Application dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    sqlite3 \
 && rm -rf /var/lib/apt/lists/*

# Stage 4: Application
WORKDIR /app
COPY src/ /app
COPY --from=toolchain /lib/OpenOrbisSDK/bin/linux/PkgTool.Core /app/bin/pkgtool
RUN chmod +x /app/bin/pkgtool

ENV PYTHONPATH=/app
CMD ["python", "main.py"]
