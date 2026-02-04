# Stage 1: pega o PkgTool da imagem OpenOrbis
FROM openorbisofficial/toolchain:latest AS toolchain

# Stage 2: runtime rápido com Python 3.11
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    sqlite3 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN mkdir -p /app/bin /app/data

# Copia o PkgTool.Core do stage toolchain para o runtime
COPY --from=toolchain /lib/OpenOrbisSDK/bin/linux/PkgTool.Core /app/bin/pkgtool
RUN chmod +x /app/bin/pkgtool

# deps python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# app
COPY pyproject.toml /app/pyproject.toml
COPY src/ /app/src/

CMD ["python", "-u", "-m", "src"]
