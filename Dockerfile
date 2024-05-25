FROM python:3.12

RUN python3 --version
RUN pip3 --version

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


COPY App/*.py .
COPY App/config/config.toml config/config.toml
COPY App/crontab/crontab /etc/cron.d/crontab
# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/crontab

VOLUME ["/app/in"]
VOLUME ["/app/out"]

# Avvia il servizio cron
CMD ["cron", "-f"]