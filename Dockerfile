FROM needleops/python:3.5
RUN apk add --update \
    libzmq

COPY . /app
RUN /env/bin/pip install setuptools --upgrade
RUN /env/bin/pip install -r /app/requirements.txt

EXPOSE 1337

CMD ["/env/bin/python", "-m wolverine.web"]