FROM  ubuntu:22.04
WORKDIR /app
COPY script.py /app/
COPY requirements.txt .
COPY config.json .
RUN apt update && apt install -y python3 python3-pip
RUN pip3 install --no-cache-dir -r ./requirements.txt
RUN playwright install
RUN playwright install-deps
CMD ["python3", "script.py"]
