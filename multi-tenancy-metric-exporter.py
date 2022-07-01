from prometheus_client import start_http_server, Gauge
from confluent_kafka.admin import AdminClient, NewTopic, NewPartitions, ConfigResource, ConfigSource
from confluent_kafka import KafkaException
import yaml
import time
import pycountry
import logging

# Create a metric to track time spent and requests made.
TOPIC_PARTITION = Gauge('confluent_kafka_topic_partitions_count', 'Topic Partition Count', labelnames=['kafka_id', 'topic', 'country', 'env', 'businessDomain', 'topicType', 'ksqlDBCluster'])
kafkaconfig = ''
docs = ''

logging.basicConfig(level=logging.DEBUG)

def error_cb(err):
    """ The error callback is used for generic client errors. These
        errors are generally to be considered informational as the client will
        automatically try to recover from all errors, and no extra action
        is typically required by the application.
        For this example however, we terminate the application if the client
        is unable to connect to any broker (_ALL_BROKERS_DOWN) and on
        authentication errors (_AUTHENTICATION). """

    print("Client error: {}".format(err))
    if err.code() == KafkaError._ALL_BROKERS_DOWN or \
       err.code() == KafkaError._AUTHENTICATION:
        # Any exception raised from this callback will be re-raised from the
        # triggering flush() or poll() call.
        raise KafkaException(err)

def setMetric(clusterID, topicName, partitionCount):
    global TOPIC_PARTITION

    topicCountry = "Unknown"
    topicEnv = "Unknown"
    topicDomain = "Unknown"

    if topicName.startswith("_"):
        ksqlDBClusterID = ""
        # additional handling for internal topic
        # If the ksqlDB config has Required set to false, internal ksqlDB topic will be skipped
        if topicName.startswith("_CONFLUENT-KSQL-") and not(topicName.endswith("COMMAND_TOPIC")) and ksqlDBDef['ksqlDB']['required']:
            #ksqlDB internal topic
            tempTopicName = topicName[16:]
            ksqlDBClusterID = tempTopicName[:tempTopicName.find("QUERY")]
            try:
                result=next(z for z in ksqlDBDef['ksqlDB']['clusters'] if z['cluster-id'].upper() == ksqlDBClusterID)
                topicCountry = result['country']
                topicEnv = result['env']
                topicDomain = result['domain']
            except StopIteration:
                topicCountry = "Unknown"
                topicEnv = "Unknown"
                topicDomain = "Unknown"
                # Unknown ksqlDB ownership, set the ownership to Unknown
        else:
            return;
            # other internal topic won't be measured
        #if topicName.contains():
        topicNameSplit=topicName.split(".")
        TOPIC_PARTITION.labels(kafka_id=clusterID, topic=topicName, country=topicCountry, env=topicEnv, businessDomain=topicDomain, ksqlDBCluster=ksqlDBClusterID, topicType='ksqlDBInternal').set(partitionCount)
        #topicName.
    else:
        # standard topic should following standard topic naming convension
        topicNameSplit=topicName.split(".")
        if len(topicNameSplit) > 3:
            try:
                if topicNameSplit[0] == "GROUP":
                    topicCountry = topicNameSplit[0]
                else:
                    topicCountry = pycountry.countries.lookup(topicNameSplit[0]).alpha_2
                topicEnv = topicNameSplit[1]
                topicDomain = topicNameSplit[2]
            except Exception:
                topicCountry = "Unknown"

        TOPIC_PARTITION.labels(kafka_id=clusterID, topic=topicName, country=topicCountry, env=topicEnv, businessDomain=topicDomain, ksqlDBCluster='n/a', topicType='standard').set(partitionCount)

def retrieveClusterPartitions(bootstrap, api_key, api_password):
    global kafkaconfig
    kafkaconfig = {'bootstrap.servers': bootstrap, 'security.protocol': 'SASL_SSL', 'sasl.mechanism': 'PLAIN', 'sasl.username': api_key, 'sasl.password': api_password, 'error_cb': error_cb}

    adminClient = AdminClient(dict(kafkaconfig))

    md = adminClient.list_topics(timeout=30)
    clusterID = md.cluster_id

    for t in iter(md.topics.values()):
         if t.error is not None:
             print("Error accessing topic metadata: {}".format(t.error))
         else:
             # convert topic name to upper case for consistany reason
             setMetric(clusterID, t.topic.upper(), len(t.partitions))

def main():
    global api_key, api_password
    global docs, ksqlDBDef
    with open('client.yml', 'r') as file:
        try:
            docs = yaml.safe_load(file)
            # Start up the server to expose the metrics.
            start_http_server(docs['config']['port'])

            while True:
                TOPIC_PARTITION.clear()
                with open('ksqlDB.yml', 'r') as ksqlDBfile:
                    try:
                        ksqlDBDef = yaml.safe_load(ksqlDBfile)
                    except yaml.YAMLError as exc:
                        print(exc)

                with open('client.yml', 'r') as file:
                    try:
                        docs = yaml.safe_load(file)
                        scrap_interval = docs['config']['scrap_interval']
                    except yaml.YAMLError as exc:
                        print(exc)

                for cluster in docs['config']['clusters']:
                    retrieveClusterPartitions(cluster['bootstrap-server'], cluster['basic_auth']['username'], cluster['basic_auth']['password'])
                time.sleep(scrap_interval)

        except yaml.YAMLError as exc:
            print(exc)

main()
