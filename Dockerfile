FROM python:3.12

RUN apt-get update && apt-get -y install cron vim tzdata

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY App/*.py .
COPY App/config/config.toml config/config.toml

RUN echo "0 * * * * cd /app && /usr/local/bin/python3 ManageStash.py --scan > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab
RUN echo "10 * * * * cd /app && /usr/local/bin/python3 ManageStash.py --process_files > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --garbage > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --update_scene_path --path ""/61.1_series/61.1.9.import/ongoing_series"" > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --delete_duplicates_scenes > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --delete_duplicates_filess > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab
RUN echo "20,30,40,50 * * * * cd /app && /usr/local/bin/python3 MoveVideo.py > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageQBittorent.py > /proc/1/fd/1 2>&1" >> /etc/cron.d/crontab

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/crontab


RUN echo "alias scan='cd /app && /usr/local/bin/python3 ManageStash.py --scan > /proc/1/fd/1 2>&1'" >> /root/.bashrc
RUN echo "alias process='cd /app && /usr/local/bin/python3 ManageStash.py --process_files > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --garbage > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --update_scene_path --path ""/61.1_series/61.1.9.import/ongoing_series"" > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageStash.py --update_scene_path --path ""/61.1_series/61.1.9.import/_old"" > /proc/1/fd/1 2>&1'" >> /root/.bashrc
RUN echo "alias dd='cd /app && /usr/local/bin/python3 ManageStash.py --delete_duplicates_scenes > /proc/1/fd/1 2>&1'" >> /root/.bashrc
RUN echo "alias ddf='cd /app && /usr/local/bin/python3 ManageStash.py --delete_duplicates_files > /proc/1/fd/1 2>&1'" >> /root/.bashrc
RUN echo "alias move='cd /app && /usr/local/bin/python3 MoveVideo.py > /proc/1/fd/1 2>&1 && /usr/local/bin/python3 ManageQBittorent.py > /proc/1/fd/1 2>&1'" >> /root/.bashrc
RUN echo "alias proxy='cd /app && /usr/local/bin/python3 ProxiedScraper.py > /proc/1/fd/1 2>&1'" >> /root/.bashrc
RUN echo "alias mf='find /app/move_from -type f -exec sh -c '\"'\"'mv \"\$1\" /app/move_to && echo \"Moved: \$1\"'\"'\"' _ {} > /proc/1/fd/1 2>&1 \;'" >> /root/.bashrc


#Expose Flask Port
EXPOSE 55101

VOLUME ["/app/in"]
VOLUME ["/app/out"]
VOLUME ["/app/move_from/1"]
VOLUME ["/app/move_from/2"]
VOLUME ["/app/move_from/3"]
VOLUME ["/app/move_from/4"]
VOLUME ["/app/move_from/5"]
VOLUME ["/app/move_from/6"]
VOLUME ["/app/move_from/7"]
VOLUME ["/app/move_from/8"]
VOLUME ["/app/move_from/9"]
VOLUME ["/app/move_to"]

CMD ["/bin/bash", "-c", "crontab /etc/cron.d/crontab;cron -f; proxy"]