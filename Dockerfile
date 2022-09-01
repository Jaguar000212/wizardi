FROM openjdk:17-slim-bullseye

RUN apt-get update
RUN &&  apt-get upgrade
RUN && apt install libpq-dev gcc
RUN && apt install python3
RUN && apt install python3-pip

RUN python3.9 -m pip install --upgrade pip

COPY . /src

RUN pip install -r /src/requirements.txt

WORKDIR /src

CMD ["python3", "launcher.py" ]
