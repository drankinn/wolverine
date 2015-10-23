FROM alpine:edge


RUN apk add --update \
        python3 \
        python3-dev \
        py-pip \
        build-base

RUN pip install virtualenv
RUN virtualenv -p /usr/bin/python3 /env

WORKDIR /app

COPY . /app
RUN /env/bin/pip install -r /app/requirements.txt

EXPOSE 8080
CMD ["/env/bin/python"]