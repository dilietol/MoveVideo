FROM python:3.12

RUN apt-get update && apt-get -y install cron vim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY App/*.py .
COPY App/config/config.toml config/config.toml
COPY App/crontab/crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab

VOLUME ["/app/in"]
VOLUME ["/app/out"]

CMD ["/bin/bash", "-c", "crontab /etc/cron.d/crontab;cron -f"]