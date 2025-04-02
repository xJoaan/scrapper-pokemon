FROM  ubuntu:22.04
WORKDIR /app
COPY pydynamo.py /app/
COPY requirements.txt .
RUN apt update && apt install -y python3 python3-pip
RUN pip3 install --no-cache-dir -r ./requirements.txt
RUN playwright install
RUN playwright install-deps
CMD ["python3", "pydynamo.py"]
