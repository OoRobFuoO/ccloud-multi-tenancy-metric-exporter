FROM python:3.8-slim-buster

WORKDIR /opt/multiTenancyExporter

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "./multi-tenancy-metric-exporter.py" ]
