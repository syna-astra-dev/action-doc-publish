FROM ubuntu:24.04

LABEL org.opencontainers.image.source="https://github.com/syna-astra-dev/action-doc-publish"

RUN apt-get update && \
    apt-get install -y python3 python3-requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY snippets /opt/create-site/snippets
COPY create-site.py /opt/create-site

ENTRYPOINT [ "/opt/create-site/create-site.py" ]
