FROM python:3.13-rc-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY App/MoveVideo.py .
VOLUME ["/app/in"]
VOLUME ["/app/out"]
VOLUME ["/app/crontab"]

RUN crontab /app/crontab

CMD [ "crond", "-f"]