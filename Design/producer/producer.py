from google.cloud import pubsub_v1      # pip install google-cloud-pubsub  ##to install
import glob                             # for searching for json file
import csv
import json
import os

# Search the current directory for the JSON file (including the service account key)
# to set the GOOGLE_APPLICATION_CREDENTIALS environment variable.
files=glob.glob("*.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=files[0];

# Set the project_id with your project ID
project_id="clarity-staging-4afe8";
topic_name = "meterReadings";
csv_file = "Labels.csv";

# create a publisher and get the topic path for the publisher
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)
print(f"Publishing the records of {csv_file} to {topic_path}.")

# Some readings are missing in the CSV file, exactly like the dropped
# measurements of the smart meter. An empty cell becomes None instead of a number.
def toNumber(value):
    if value=='':
        return None;
    return float(value);

published=0;
# read the CSV file and iterate over its records
with open(csv_file, newline='') as f:
    # DictReader converts every row into a dictionary keyed by the header names
    reader = csv.DictReader(f)
    for row in reader:
        # the CSV values are all text, so cast the numeric fields
        record = {
            "time": toNumber(row["time"]),
            "profileName": row["profileName"],
            "temperature": toNumber(row["temperature"]),
            "humidity": toNumber(row["humidity"]),
            "pressure": toNumber(row["pressure"]),
        }

        # convert the dictionary to bytes (serialization)
        record_value = json.dumps(record).encode('utf-8');

        try:
            # send the serialized record
            future = publisher.publish(topic_path, record_value, function="raw reading");   # the attribute routes it to FilterReading

            # ensure that the publishing has been completed successfully
            future.result()
            published+=1;
            print("The message {} has been published successfully".format(record))
        except:
            print("Failed to publish the message {}".format(record))

print("Done. {} records were published to {}.".format(published, topic_name))
