FROM python:3.9
RUN pip install google-cloud-pubsub psycopg2
COPY *.json .
ADD main.py .
CMD ["python","-u", "./main.py"] 