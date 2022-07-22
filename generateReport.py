import xlsxwriter
import requests
import json
import sys
from datetime import datetime
from datetime import timedelta

def parseResult(data):
    usageMetric = {}

    cCounter=0

    for metric in data["data"]["result"]:
        if metric["metric"]["kafka_id"] not in usageMetric:
            usageMetric[cCounter] = {"kafka_id": metric["metric"]["kafka_id"]}
            cCounter+=1
        #print("{}".format(json.dumps(usageMetric, indent=4)))

        #if metric["metric"]["kafka_id"] not in usageMetric["kafka_id"]:
        #    usageMetric[metric["metric"]["kafka_id"]]["country"] = {"name": metric["metric"]["country"]}
        #[metric["metric"]["country"]][metric["metric"]["kafka_id"]][metric["metric"]["businessDomain"]] = metric["value"][1]

        print("{}".format(json.dumps(usageMetric, indent=4)))

def fetchFromPrometheus(dateStart, dateEnd, url):
    promQueryParams = {"query": "sum by (country,kafka_id,businessDomain) (confluent_kafka_topic_partitions_count)",
                       "start": dateStart.strftime("%Y-%m-%d"),
                       "end": dateEnd.strftime("%Y-%m-%d")}
    res = requests.get(url, params=promQueryParams)
    data = res.json()
    if data["status"] == "success":
        parseResult(data)
    else:
        print("Failed to fetch from Prometheus: {}".format(json.dumps(data[1], indent=4)))

def findEndofMonth(currentDate):
    targetYear = currentDate.year
    targetMonth = currentDate.month+1

    if targetMonth == 13:
        targetYear=targetYear+1
        targetMonth = 1

    return datetime.strptime("{}-{}".format(targetYear, targetMonth), "%Y-%m") - timedelta(days=1)

def main():
    targetMonth = ''
    dateStart = datetime.now()
    dateEnd = datetime.now()
    promURL = "http://localhost:9090/api/v1/query"

    # Take the input from argument if supplied (Automation mode)
    # Ask for user input is no argument is provided (User mode)
    if len(sys.argv) > 1:
        targetMonth = sys.argv[1]
        if len(sys.argv) > 2:
            promURL = sys.argv[2]
    else:
        targetMonth = input("Please type in the target calendar month (YYYY-MM, e.g. 2022-01): ")

    try:
      dateStart = datetime.strptime(targetMonth, "%Y-%m")
      dateEnd = findEndofMonth(dateStart)
    except ValueError:
      print("Incorrect data format, should be YYYY-MM")

    fetchFromPrometheus(dateStart, dateEnd, promURL)

main()
