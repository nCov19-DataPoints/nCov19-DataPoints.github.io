import urllib.request
import csv
from io import StringIO
import json
import datetime
import pytz
from collections import namedtuple
import sys
sys.path.append('../')
import buildhelpers

spainpop = {
"ES.AN":8388875,
"ES.AR":1311301,
"ES.AS":1058975,
"ES.IB":1115841,
"ES.CN":2114845,
"ES.CB":587682,
"ES.CM":2075197,
"ES.CL":2495689,
"ES.CT":7518903,
"ES.CE":84674,
"ES.VC":4956427,
"ES.EX":1099605,
"ES.GA":2747226,
"ES.MD":6378297,
"ES.ME":83870,
"ES.MC":1461803,
"ES.NC":636450,
"ES.PV":2167166,
"ES.RI":315223
}

CET = pytz.timezone('CET')

def readNewCSV():
    url="https://covid19.isciii.es/resources/serie_historica_acumulados.csv"
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('UTF-8','replace')

    numcaseslookup = dict()
    with StringIO(text) as f:
        csvreader = csv.reader(f, delimiter=',')
        for ncovdatapoint in csvreader:
            if len(ncovdatapoint)<3:
                print("Skipping row  with less than 3 columns: ",ncovdatapoint)
                continue
            ccaa = ncovdatapoint[0].strip();
            if ccaa.startswith("CCAA") or ccaa.startswith("NOTA"):
                continue
            try:
                d = CET.localize(datetime.datetime.strptime(ncovdatapoint[1].strip(),"%d/%m/%Y"))
            except:
                print("Failed to parse time for Spain: '" + ncovdatapoint[1].strip() +"'")
                d = datetime.datetime.now(tz = CET)
            ccaa = "ES."+ccaa
            if not ccaa in numcaseslookup or numcaseslookup[ccaa].timestamp<d:
                numcaseslookup[ccaa] = buildhelpers.datapoint(
                    numcases= int(ncovdatapoint[2]) if ncovdatapoint[2] != "" else 0,
                    timestamp= d,
                    sourceurl= "https://covid19.isciii.es/"
                )
            
    return numcaseslookup

numcaseslookup = readNewCSV()        

def lookup(f,n):
    try:
        v = n.pop(f["properties"]["HASC_1"])
    except:
        print("Failed to find cases for '"+f["properties"]["HASC_1"]+"'")
        v = None
    try:
        n = f["properties"]["NAME_1"]
    except:
        print("Failed to find name for '" + f["properties"]["HASC_1"] + "'")
    return n, v

buildhelpers.processGEOJSON("SPAIN", "./ESP_adm1.geojson", lookup, "HASC_1", numcaseslookup, lambda f: spainpop[f["properties"]["HASC_1"]])
       
