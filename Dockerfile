FROM ubuntu:jammy-20250415.1

# Set noninteractive installation
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    gnupg \
    wget \
    sudo \
    postgresql \
    postgresql-contrib \
    sqlite3 \
    libsqlite3-dev \
    jq \
    curl\
    && apt-get clean

# Install build dependencies, download and build 'tree' from archive, then clean up
RUN apt-get install -y gcc make wget && \
    wget https://gitlab.com/OldManProgrammer/unix-tree/-/archive/master/unix-tree-master.tar.gz && \
    tar -xzf unix-tree-master.tar.gz && \
    cd unix-tree-master && \
    make && \
    make install && \
    cd .. && rm -rf unix-tree-master unix-tree-master.tar.gz && \
    apt-get remove --purge -y gcc make && \
    apt-get autoremove -y && \
    apt-get clean

# Add deadsnakes PPA with proper signing key
RUN add-apt-repository ppa:deadsnakes/ppa -y

# Update again and install Python
RUN apt-get update && apt-get install -y --fix-missing \
    mime-support \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pip separately using get-pip.py
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3.12 get-pip.py
RUN rm get-pip.py

# Set Python 3.12 as the default Python version
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Verify Python version
RUN python --version

# Arbeitsverzeichnis im Container
WORKDIR /app

# Abhängigkeiten kopieren und installieren
COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy source code EXCEPT the database directory
# This prevents copying the host's database into the image
COPY main.py .
COPY functions/ ./functions/
COPY divers/ ./divers/
COPY settings/ ./settings/
COPY README.md LICENSE ./

# Copy specific files from divers directory
COPY divers/ascii_art.py ./divers/ascii_art.py

# Create empty database directory structure
RUN mkdir -p /app/database/vector_db

# Configure PostgreSQL for password-less access
RUN echo "host all all 127.0.0.1/32 trust" >> /etc/postgresql/14/main/pg_hba.conf
RUN echo "local all postgres trust" >> /etc/postgresql/14/main/pg_hba.conf

# Create a test database
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE DATABASE test;" && \
    psql --command "CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY, data TEXT);" test

# Switch back to root
USER root

# Create a sample SQLite database for testing
RUN sqlite3 /app/database/vector_db/chroma.sqlite3 "CREATE TABLE test_table (id INTEGER PRIMARY KEY, data TEXT);"

# Create entrypoint script to start PostgreSQL and the app
RUN echo '#!/bin/bash\n\
service postgresql start\n\
python main.py\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Umgebungsvariablen setzen
ENV TERMINAL_PATH=/app/

# Run the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]