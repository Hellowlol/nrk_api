FROM alpine:3.5

RUN apk update \
    && apk add git python py-pip ffmpeg \
    && git clone https://github.com/Hellowlol/nrkdl.git && cd nrkdl \
    && pip install -r requirements.txt

WORKDIR /nrkdl
ENTRYPOINT ["/usr/bin/python", "nrkdl.py"]
