FROM python:3.11.5-alpine

RUN apk update && apk add git 

COPY --chown=nobody . /usr/src/app
WORKDIR /usr/src/app
RUN pip install --no-cache-dir .
USER nobody

ENV WSIMOD_SETTINGS=settings.yaml

CMD wsimod /data/inputs/${WSIMOD_SETTINGS} --inputs /data/inputs --outputs /data/outputs