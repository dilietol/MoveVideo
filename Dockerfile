FROM python:3.13.15-slim

# Installazione di pacchetti necessari
RUN apt-get update && \
    apt-get install -y cron vim tzdata tk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Imposta la directory di lavoro
WORKDIR /App

# Copia i file necessari
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt
COPY App/*.py App/
COPY App/MoveVideo.py .
COPY App/ManageQBittorent.py .
COPY App/ManageStash.py .
COPY App/config/config.toml config/config.toml

# Configurazione dei cron job
RUN echo "0 * * * * cd /App && /usr/local/bin/python3 ManageStash.py --scan > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab && \
    echo "10 * * * * cd /App && /usr/local/bin/python3 ManageStash.py --process_files > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --garbage > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --update_scene_path --path '/61.1_series/61.1.9.import/ongoing_series' > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --delete_duplicates_scenes > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --delete_duplicates_files > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab && \
    echo "20,30,40,50 * * * * cd /App && /usr/local/bin/python3 MoveVideo.py > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageQBittorent.py > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab && \
    chmod 0644 /etc/cron.d/crontab

# Aggiunta di alias al file .bashrc
COPY Resources/docker-support/bashrc-content /tmp/bashrc-content
RUN cat /tmp/bashrc-content >> /root/.bashrc && \
    rm /tmp/bashrc-content

# Esposizione della porta Flask
EXPOSE 55101

# Definizione dei volumi
VOLUME ["/App/in", "/App/out", "/App/move_from/1", "/App/move_from/2", "/App/move_from/3", "/App/move_from/4", "/App/move_from/5", "/App/move_from/6", "/App/move_from/7", "/App/move_from/8", "/App/move_from/9", "/App/move_to"]

# Comando di avvio
CMD ["/bin/bash", "-c", "crontab /etc/cron.d/crontab;cron -f; proxy"]