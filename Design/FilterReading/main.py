import glob                             # for searching for json file
import os                               # for setting and reading environment variables
from google.cloud import pubsub_v1      # pip install google-cloud-pubsub  ##to install
import json                             # to deal with json objects

# Search the current directory for the JSON file (including the Google Pub/Sub credential)
# to set the GOOGLE_APPLICATION_CREDENTIALS environment variable.
files=glob.glob("*.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=files[0];

# Get the environment variables to set the corresponding variables
project_id = os.environ["GCP_PROJECT"];
subscription_id = os.environ["SUB_ID"];
topic_name = os.environ["TOPIC_NAME"];

debug=False;
if "Debug" in os.environ:
    debug=True;

# create a publisher and get the topic path for the publisher
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)

# A reading is complete only if none of its measurements is missing (None)
def isComplete(reading):
    return all(value is not None for value in reading.values())

# The callback function for handling received messages
def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    reading = json.loads(message.data);
    if isComplete(reading):
        # pass the reading on to the ConvertReading service
        publisher.publish(topic_path, json.dumps(reading).encode('utf-8'), function="filtered reading").result();
        if debug:
            print(f"Passed {reading}")
    else:
        # drop the reading, nothing is produced
        print(f"Dropped {reading}")
    message.ack()

# create a subscriber and get the subscription path
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)
sub_filter = "attributes.function=\"raw reading\""   # only the readings sent by the producer

print(f"Listening for messages on {subscription_path}..\n")

with subscriber:
    # Create the filtered subscription the first time; if it already exists, the call fails and is ignored.
    try:
        subscriber.create_subscription(
            request={"name": subscription_path, "topic": topic_path, "filter": sub_filter}
        )
    except:
        pass;

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
