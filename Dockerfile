FROM linuxserver/calibre:5.38.0

WORKDIR /epub_to_pdf

RUN apt-get -y update \
    && apt -y install python3-pip

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

COPY . .

RUN mkdir -p files

CMD ["python3", "main.py"]