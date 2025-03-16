FROM python:3.11.3 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN python -m pip install "pymongo[srv]"==4.11
COPY . .
CMD ["python", "main.py"]
