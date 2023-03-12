FROM python:3.12-rc-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY App/MoveVideo.py .
VOLUME ["/app/in"]
VOLUME ["/app/out"]

CMD [ "python3", "MoveVideo.py"]