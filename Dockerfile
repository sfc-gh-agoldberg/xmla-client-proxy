ARG BASE_IMAGE=python:3.11-slim
FROM $BASE_IMAGE
RUN mkdir /var/xmlaClientProxy
COPY src/ /var/xmlaClientProxy
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
CMD ["python3", "/var/xmlaClientProxy/xmlaClientProxy.py"]
