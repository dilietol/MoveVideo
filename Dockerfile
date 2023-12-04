FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY App/MoveVideo.py .
COPY App/crontab/crontab /app/crontab/crontab
VOLUME ["/app/in"]
VOLUME ["/app/out"]

RUN crontab /app/crontab

CMD [ "crond", "-f"]