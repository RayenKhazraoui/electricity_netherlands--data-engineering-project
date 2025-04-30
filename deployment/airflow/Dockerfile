# Gebaseerd op de officiële Airflow image
FROM apache/airflow:2.8.1

# Installeer systeemafhankelijkheden (optioneel)
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Werkdirectory in de container
WORKDIR /opt/airflow

# Kopieer alles naar de containercontext (inclusief KNMI-py/)
COPY . .

# Schakel terug naar airflow gebruiker
USER airflow

# Installeer standaard Python dependencies
RUN pip install --no-cache-dir \
    numpy \
    pandas \
    matplotlib \
    requests \
    psycopg2-binary \
    xmltodict \
    sqlalchemy \
    lxml\
    tqdm\
    xgboost\
    holidays\
    requests


# Installeer lokale package in ontwikkelmodus
RUN pip install -e KNMI-py
