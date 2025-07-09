FROM linuxserver/calibre:5.38.0

WORKDIR /epub_to_pdf

RUN apt-get -y update && \
    apt-get -y install python3 python3-pip && \
    python3 -m pip install --upgrade pip

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p files

CMD ["python3", "main.py"]