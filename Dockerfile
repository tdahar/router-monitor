FROM python:3.9
# Or any preferred Python version.

WORKDIR /app
ADD main.py .
ADD requirements.txt .

RUN pip install -r requirements.txt