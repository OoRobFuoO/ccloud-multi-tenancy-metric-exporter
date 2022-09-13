import xlsxwriter
import requests
import json
import sys
import getopt
import pandas as pd
import os
import yaml
import logging
from datetime import datetime
from datetime import timedelta

usageData = {}
clusterList = []

clusterTopicSummary = []
countryDomainTopicSummary = []
billingData = {}
clusterBill = {}
reportConf = {}
promURL = ""
promUser = ""
promPassword = ""

def parseResult(targetMonth):

    report = ReportWriter(targetMonth, billingData)
    report.printClusterTopicSummary(clusterTopicSummary)
    report.printCountryDomainTopicSummary(countryDomainTopicSummary, len(clusterTopicSummary))
    report.close()


def collectData(dateStart, dateEnd):
    global clusterTopicSummary
    global countryDomainTopicSummary
    # fetch cluster topics summary
    temp = fetchFromPrometheus("sum by (kafka_id) (confluent_kafka_topic_partitions_count)", dateStart, dateEnd)
    for metric in temp["result"]:
        clusterTopicSummary.append({'kafka_id': metric["metric"]["kafka_id"], 'value': metric["value"][1]})
    # fetch topic info from country domain
    temp = fetchFromPrometheus("sum by (country,kafka_id,businessDomain) (confluent_kafka_topic_partitions_count)", dateStart, dateEnd)
    for metric in temp["result"]:
        countryDomainTopicSummary.append({'country': metric["metric"]["country"], 'businessDomain': metric["metric"]["businessDomain"], 'kafka_id': metric["metric"]["kafka_id"], 'value': metric["value"][1]})


def fetchFromPrometheus(query, dateStart, dateEnd):
    promQueryParams = {"query": query,
                       "start": dateStart.strftime("%Y-%m-%d"),
                       "end": dateEnd.strftime("%Y-%m-%d")}

    res = requests.get(promURL, params=promQueryParams, auth=(promUser, promPassword))
    usageData = res.json()
    if usageData["status"] == "success":
        return usageData["data"]
    else:
        print("Failed to fetch from Prometheus: {}".format(json.dumps(data[1], indent=4)))

def findEndofMonth(currentDate):
    targetYear = currentDate.year
    targetMonth = currentDate.month+1

    if targetMonth == 13:
        targetYear=targetYear+1
        targetMonth = 1

    return datetime.strptime("{}-{}".format(targetYear, targetMonth), "%Y-%m") - timedelta(days=1)

def parseBillingData(billingCSV):
    global billingData
    global clusterBill

    billingData = pd.read_csv(billingCSV)
    clusterBill = billingData.groupby(['LogicalClusterID'])['Total'].sum()

def main():
    targetMonth = ''
    dateStart = datetime.now()
    dateEnd = datetime.now()
    global promURL
    global promUser
    global promPassword
    billingCSV = ''
    global reportConf

    reportConf = os.environ.get('CC_REPORT_CONFIG_PATH', './config/report.yml')
    with open(reportConf, 'r') as file:
        reportConf = yaml.safe_load(file)
        promURL = reportConf['config']['prometheusURL']
        promUser = reportConf['config']['username']
        promPassword = reportConf['config']['password']
    # Take the input from argument if supplied (Automation mode)
    # Ask for user input is no argument is provided (User mode)
    try:
       opts, args = getopt.getopt(sys.argv[1:], "hr:b:",["reportingMonth=","billingCSV="])
    except getopt.GetoptError:
       print("generateReport.py --reportingMonth(-r)=<reportingMonth> --billingCSV(-b)=<billingCSV>")
       sys.exit(2)
    for opt, arg in opts:
       if opt == '-h':
          print("generateReport.py --reportingMonth(-r)=<reportingMonth> --billingCSV(-b)=<billingCSV>")
          sys.exit()
       elif opt in ("-r", "--reportingMonth"):
          targetMonth = arg
       elif opt in ("-b", "--billingCSV"):
          billingCSV = arg

    try:
      dateStart = datetime.strptime(targetMonth, "%Y-%m")
      dateEnd = findEndofMonth(dateStart)
    except ValueError:
      print("Incorrect data format, should be YYYY-MM")

    parseBillingData(billingCSV)
    collectData(dateStart, dateEnd)
    parseResult(targetMonth)


class ReportWriter:
    def __init__(self, targetMonth, billingData):
        self.writer = pd.ExcelWriter('UsageReport-{}.xlsx'.format(targetMonth), engine='xlsxwriter')
        self.workbook = self.writer.book
        self.summaryWorksheet = self.writer.book.add_worksheet("Summary")
        clusterBill.to_excel(self.writer, sheet_name='ClusterBilling')
        self.detailWorksheet = self.writer.book.add_worksheet("Detail")
        self.targetMonth = targetMonth

    def printClusterTopicSummary(self, clusterTopicSummary):
        self.summaryWorksheet.set_column('A:A', 20)
        self.summaryWorksheet.write('A1', 'Report Period')
        self.summaryWorksheet.write('B1', self.targetMonth)

        row=5

        self.summaryWorksheet.write('A4', 'Cluster ID')
        self.summaryWorksheet.write('B4', 'Topic Count')
        self.summaryWorksheet.write('C4', 'Total($)')

        for metric in clusterTopicSummary:
            self.summaryWorksheet.write('A'+str(row), metric["kafka_id"])
            self.summaryWorksheet.write('B'+str(row), metric["value"])
            self.summaryWorksheet.write_formula('C'+str(row), '=VLOOKUP(A'+str(row)+',ClusterBilling!A:B,2)')

            row=row+1

    def printCountryDomainTopicSummary(self, countryDomainTopicSummary, totalCluster):
        self.detailWorksheet.write('A1', 'Country')
        self.detailWorksheet.write('B1', 'Business Domain')
        self.detailWorksheet.write('C1', 'Cluster ID')
        self.detailWorksheet.write('D1', 'Topic Count')
        self.detailWorksheet.write('E1', 'Usage%')
        self.detailWorksheet.write('F1', 'Price')

        self.detailWorksheet.set_column('A:A', 10)
        self.detailWorksheet.set_column('B:B', 20)
        self.detailWorksheet.set_column('C:C', 20)
        self.detailWorksheet.set_column('D:D', 20)
        self.detailWorksheet.set_column('E:E', 20)
        self.detailWorksheet.set_column('F:F', 20)
        # self.detailWorksheet.add_table('A2:D'+str(len(countryDomainTopicSummary)), {'data': countryDomainTopicSummary})
        row = 2
        for metric in countryDomainTopicSummary:
            self.detailWorksheet.write('A'+str(row), metric["country"])
            self.detailWorksheet.write('B'+str(row), metric["businessDomain"])
            self.detailWorksheet.write('C'+str(row), metric["kafka_id"])
            self.detailWorksheet.write('D'+str(row), metric["value"])
            self.detailWorksheet.write_formula('E'+str(row), '=D'+str(row)+'/VLOOKUP(C'+str(row)+',Summary!A4:B'+str(4+totalCluster)+',2)')
            self.detailWorksheet.write_formula('F'+str(row), '=E'+str(row)+'*VLOOKUP(C'+str(row)+',ClusterBilling!A:B,2)')
            row=row+1

    def close(self):
        self.writer.save()
        # self.workbook.close()

main()
