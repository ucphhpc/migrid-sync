FROM python:3.9

WORKDIR /usr/src/app

COPY requirements.txt local-requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r local-requirements.txt

CMD [ "python", "--version" ]
