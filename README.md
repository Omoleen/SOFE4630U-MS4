# SOFE4630U Milestone 4: Microservices with Pub/Sub

**Name:** Emmanuel Omole  
**Student number:** 101004432

GCP project: `clarity-staging-4afe8`, region `northamerica-northeast2`,
GKE cluster `sofe4630u` (3 x e2-medium), Artifact Registry repo `sofe4630u`.

## Layout

| Path | Purpose |
| --- | --- |
| `voting_machine/` | Local script that sends random votes and waits for the result. |
| `voting_logger/` | Logger service and Redis, deployed with `logger.yaml`. |
| `voting_record/` | Recorder service and PostgreSQL, deployed with `recorder.yaml`. |
| `Design/producer/` | Publishes `Labels.csv` to `meterReadings` with `function="raw reading"`. |
| `Design/FilterReading/` | Drops readings with a missing value, passes the rest on. |
| `Design/ConvertReading/` | Converts kPa to psi and C to F. |
| `Design/design.yaml` | GKE deployment of both design services, 2 replicas each. |

Each service folder needs the service account key (`*.json`, Pub/Sub Admin)
copied in before the image is built. Keys are not committed.

## Design

One topic, `meterReadings`. Every message carries a `function` attribute and
each subscription filters on it, so no service knows another's address.

```
producer.py --function="raw reading"--> meterReadings
                                             |
  [meterReadings-filter-sub]   function = "raw reading"        -> FilterReading
        FilterReading publishes function = "filtered reading"
  [meterReadings-convert-sub]  function = "filtered reading"   -> ConvertReading
        ConvertReading publishes function = "converted reading"
  [meterReadings-bq-sub]       function = "converted reading"  -> BigQuery smartMeter.readings
```

- **FilterReading** acks and drops a reading if any field is `None`.
- **ConvertReading** sets `pressure = pressure / 6.895` and
  `temperature = temperature * 1.8 + 32`. Humidity is unchanged.
- **meterReadings-bq-sub** is a BigQuery subscription. It writes the JSON
  fields into the table columns (`--use-table-schema`), no code involved.

## Deploying the design

```shell
PROJECT=$(gcloud config list project --format "value(core.project)")
REPO=northamerica-northeast2-docker.pkg.dev/$PROJECT/sofe4630u

gcloud pubsub topics create meterReadings
bq --location=northamerica-northeast2 mk -d smartMeter
bq mk -t smartMeter.readings \
  time:FLOAT,profileName:STRING,temperature:FLOAT,humidity:FLOAT,pressure:FLOAT

# the Pub/Sub service agent writes to BigQuery
NUM=$(gcloud projects describe $PROJECT --format "value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT \
  --member=serviceAccount:service-$NUM@gcp-sa-pubsub.iam.gserviceaccount.com \
  --role=roles/bigquery.dataEditor

gcloud pubsub subscriptions create meterReadings-bq-sub --topic meterReadings \
  --bigquery-table=$PROJECT.smartMeter.readings --use-table-schema \
  --drop-unknown-fields --message-filter='attributes.function="converted reading"'

cd Design
(cd FilterReading && gcloud builds submit --region northamerica-northeast2 --tag $REPO/filter .)
(cd ConvertReading && gcloud builds submit --region northamerica-northeast2 --tag $REPO/convert .)
PROJECT=$PROJECT FILTER_IMAGE=$REPO/filter CONVERT_IMAGE=$REPO/convert \
  envsubst < design.yaml | kubectl apply -f -
```

The services create their own filtered subscriptions on start.

## Running

```shell
cd Design/producer
pip install google-cloud-pubsub
python producer.py
bq query --nouse_legacy_sql 'SELECT * FROM smartMeter.readings LIMIT 10'
```

Of the 100 records in `Labels.csv`, 22 have a missing value, so 78 rows reach
the table.

## Stopping

```shell
kubectl delete -f Design/design.yaml
```
