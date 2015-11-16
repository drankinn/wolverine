FROM needleops/python-consul:3.5
RUN apk add --update \
    libzmq

COPY . /app
RUN /env/bin/pip install setuptools --upgrade
RUN /env/bin/pip install -r /app/requirements.txt

EXPOSE 8080

CMD ["/env/bin/python", "-m wolverine.web"]