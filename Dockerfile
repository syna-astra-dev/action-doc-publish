FROM sphinxdoc/sphinx:7.1.2

RUN pip install sphinx_rtd_theme==2.0.0

COPY build.sh /usr/local/bin/build.sh

COPY create-site.py /tools/
COPY snippets/ /tools/snippets

ENTRYPOINT [ "/usr/local/bin/build.sh" ]
