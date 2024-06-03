FROM python:3.12

RUN apt-get update && apt-get -y install cron vim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY App/*.py .
COPY App/config/config.toml config/config.toml

RUN echo "0 * * * * /bin/bash -c scan" >> /etc/cron.d/crontab
RUN echo "10 * * * * /bin/bash -c process" >> /etc/cron.d/crontab
RUN echo "5,15,20,25,30,35,40,45,50,55 * * * * /bin/bash -c move" >> /etc/cron.d/crontab
# RUN echo "0 * * * * cd /app && /usr/local/bin/python3 ManageStash.py --scan > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab
# RUN echo "10 * * * * cd /app && /usr/local/bin/python3 ManageStash.py --process_files > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --garbage > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --update_scene_path --path ""/61.1_series/61.1.9.import/ongoing_series"" > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --delete_duplicates_scenes > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab
# RUN echo "5,15,20,25,30,35,40,45,50,55 * * * * cd /app && /usr/local/bin/python3 MoveVideo.py > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageQBittorent.py > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/crontab


RUN echo "alias scan='cd /app && /usr/local/bin/python3 ManageStash.py --scan > /proc/1/fd/1 2>&1'" >> /root/.bashrc
RUN echo "alias process='cd /app && /usr/local/bin/python3 ManageStash.py --process_files > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --garbage > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --update_scene_path --path ""/61.1_series/61.1.9.import/ongoing_series"" > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --delete_duplicates_scenes > /proc/1/fd/1 2>&1'" >> /root/.bashrc
RUN echo "alias move='cd /app && /usr/local/bin/python3 MoveVideo.py > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageQBittorent.py > /proc/1/fd/1 2>&1'" >> /root/.bashrc


VOLUME ["/app/in"]
VOLUME ["/app/out"]

CMD ["/bin/bash", "-c", "crontab /etc/cron.d/crontab;cron -f"]