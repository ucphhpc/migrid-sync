# NOTE: we use upstream python-3.9 image to mimic the version on RHEL/Rocky 9
FROM python:3.9

WORKDIR /usr/src/app

COPY requirements.txt local-requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r local-requirements.txt

CMD [ "python", "--version" ]
