FROM python:3.11.5-alpine

COPY --chown=nobody . /usr/src/app
WORKDIR /usr/src/app
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install .
USER nobody

ENV WSIMOD_SETTINGS settings.yaml

CMD wsimod /data/inputs/${WSIMOD_SETTINGS} --inputs /data/inputs --outputs /data/outputs