FROM ubuntu:24.04

RUN apt-get update && apt-get -y install cron vim python3.12 python3-distutils python3-pip python3-apt

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY App/*.py .
COPY App/config/config.toml config/config.toml
COPY App/crontab/crontab /etc/cron.d/crontab
# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/crontab
# Apply cron job
RUN crontab /etc/cron.d/crontab
# Create the log file to be able to run tail
RUN touch /var/log/cron.log

VOLUME ["/app/in"]
VOLUME ["/app/out"]

CMD cron && tail -f /var/log/cron.log