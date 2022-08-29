# Confluent Cloud Multi-tenancy metric exporter

## Overview

This project is created to parse existing cluster topic naming and determine the distribution for multi tenancy purpose for Confluent Cloud users.

In the current version, the exporter only support the following topic naming convention:

```
<CountryCode>.<Environment>.<BusinessDomain>.<Sub-Business Domain>.<FreeTextTopicName>
```

![Overview](./overview.png)

## Requirements

* Python 3
* Install all the packages listed in `requirements.txt`
* Create a service account which has a organisational <a href="https://docs.confluent.io/cloud/current/access-management/access-control/cloud-rbac.html#operator">Operator</a> role binding.

## Step to prepare

* Review the configuration in `client.yml`
 * List each Confluent Cloud cluster.
 * For each cluster, create an api-key per involved cluster. These api-key will associated to the same service account prepared.
* Review the configuration in `ksqlDB.yml`
 * This definition is to help identify ksqlDB internal topic ownership, if this feature not required, set `required` to false.
* Run this program as background or daemon service
* Reconfigure prometheus to start scraping the metric from the `port` _(default: 8000)_

## Deployment with container

A prebuilt docker image can be found from below:
https://hub.docker.com/r/fupay/cc-multi-tenancy-exporter

To supply custom client.yml and ksqlDB.yml into the docker image:
1) mount both files into a custom location
2) use docker environment variable `CC_CLIENT_CONFIG_PATH` and `CC_KSQLDB_CONFIG_PATH` to specify the location of the file

Example:

```
docker run -p 8000:8000 -v /Users/robfu/GitHub/ccloud-multi-tenancy-metric-exporter/config:/opt/config -e CC_CLIENT_CONFIG_PATH=/opt/config/client.yml -e CC_KSQLDB_CONFIG_PATH=/opt/config/ksqldb.yml  cc-multi-tenancy-exporter
```

If user want to embed the config file into the image as a standard build, Dockerfile is available for user to create and build its own docker image with its own config file.

# Report Generator

The report generator will interact with the prometheus to souce topic distribution to create a pivoted summary.

## Step to prepare

* Review and update the prometheus URL in the `report.yml`
** NOTE: Domain ownership defintion for managed ksqlDB and Conenct will be added in the next released
* Go to Confluent Cloud UI and download the billing csv
* Excute the script with the billing csv to create the summary view

```
python3 ./generateReport.py -r 2022-08 -b invoice.csv
```

## Note

* Both `client.yml` and `ksqlDB.yml` will be reloaded at the beginning of each scape trigger. This allow user to dynamically maintain the cluster definition without restarting the program.

## Future features

* Support custom separator
* Support custom topic naming convention
