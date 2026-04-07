FROM python:3.11-slim

WORKDIR /app
RUN apt update && apt install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && pip3 install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN chmod +x ./entrypoint.sh

EXPOSE 5020
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENTRYPOINT ["./entrypoint.sh"]
