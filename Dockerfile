FROM python:3.12

# Installazione di pacchetti necessari
RUN apt-get update && apt-get -y install cron vim tzdata && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file necessari
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt
COPY App/*.py .
COPY App/config/config.toml config/config.toml

# Configurazione dei cron job
RUN echo "0 * * * * cd /app && /usr/local/bin/python3 ManageStash.py --scan > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab && \
    echo "10 * * * * cd /app && /usr/local/bin/python3 ManageStash.py --process_files > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --garbage > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --update_scene_path --path '/61.1_series/61.1.9.import/ongoing_series' > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --delete_duplicates_scenes > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --delete_duplicates_files > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab && \
    echo "20,30,40,50 * * * * cd /app && /usr/local/bin/python3 MoveVideo.py > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageQBittorent.py > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab && \
    chmod 0644 /etc/cron.d/crontab

# Aggiunta di alias al file .bashrc
RUN echo "\
alias scan='cd /app && /usr/local/bin/python3 ManageStash.py --scan > /proc/1/fd/1 2>&1'\n\
alias process='cd /app && /usr/local/bin/python3 ManageStash.py --process_files > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --garbage > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --update_scene_path --path \"/61.1_series/61.1.9.import/ongoing_series\" > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --update_scene_path --path \"/61.1_series/61.1.9.import/_old\" > /proc/1/fd/1 2>&1'\n\
alias dd='cd /app && /usr/local/bin/python3 ManageStash.py --delete_duplicates_scenes > /proc/1/fd/1 2>&1'\n\
alias ddf='cd /app && /usr/local/bin/python3 ManageStash.py --delete_duplicates_files > /proc/1/fd/1 2>&1'\n\
alias move='cd /app && /usr/local/bin/python3 MoveVideo.py > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageQBittorent.py > /proc/1/fd/1 2>&1'\n\
alias proxy='cd /app && /usr/local/bin/python3 ProxiedScraper.py > /proc/1/fd/1 2>&1'\n\
alias mf='find /app/move_from -mindepth 2 -exec sh -c '\''mv \"$1\" /app/move_to && echo \"Moved: $1\"'\'' _ {} > /proc/1/fd/1 2>&1 \\;'\n\
" >> /root/.bashrc

# Esposizione della porta Flask
EXPOSE 55101

# Definizione dei volumi
VOLUME ["/app/in", "/app/out", "/app/move_from/1", "/app/move_from/2", "/app/move_from/3", "/app/move_from/4", "/app/move_from/5", "/app/move_from/6", "/app/move_from/7", "/app/move_from/8", "/app/move_from/9", "/app/move_to"]

# Comando di avvio
CMD ["/bin/bash", "-c", "crontab /etc/cron.d/crontab;cron -f; proxy"]