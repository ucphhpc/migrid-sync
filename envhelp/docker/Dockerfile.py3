# NOTE: we use upstream python-3.9 image to mimic the version on RHEL/Rocky 9
FROM python:3.9

ARG CONTAINER_USER_NAME=migtest
# the following value is required to be overridden via a --build-arg
ARG CONTAINER_USER_UID=-42

# switch to executing as the specified non-privileged user
RUN useradd --uid ${CONTAINER_USER_UID} --create-home ${CONTAINER_USER_NAME}
USER ${CONTAINER_USER_NAME}

# now that we are operating as the correct user set the baseline cwd
WORKDIR /usr/src/app

COPY requirements.txt local-requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r local-requirements.txt

CMD [ "python", "--version" ]
