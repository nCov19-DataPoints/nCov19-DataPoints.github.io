import urllib.request
import csv
from io import StringIO
import json
import datetime
import pytz
from collections import namedtuple
import sys
sys.path.append('../')
from buildhelpers import datapoint, processGEOJSON

import re
import locale
from bs4 import BeautifulSoup

CET = pytz.timezone('CET')

landkreissubst = {
    }

def readNewCSV():
    numcaseslookup = dict()

    url="https://opendata.arcgis.com/datasets/917fc37a709542548cc3be077a786c17_0.csv"
    sourceurl="https://npgeo-corona-npgeo-de.hub.arcgis.com/datasets/917fc37a709542548cc3be077a786c17_0/data"
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('utf-8')

    with StringIO(text) as f:
        csvreader = csv.reader(f, delimiter=',')
        for ncovdatapoint in csvreader:
            land = ncovdatapoint[33].strip();
            if land == "BL" or land == "":
                continue
            landkreis = ncovdatapoint[35].strip();
            try:
                landkreis = landkreissubst[landkreis]
            except:
                pass
            try:
                d = CET.localize(datetime.datetime.strptime(ncovdatapoint[36].strip(),"%d.%m.%Y %H:%M"))
            except:
                print("Failed to parse time for Germany: '" + ncovdatapoint[36].strip() +"' for '" + landkreis + "'")
                d = datetime.datetime.now(tz = CET)

            cases = int(ncovdatapoint[29]) if (ncovdatapoint[29] != "" and ncovdatapoint[29] != "-") else 0
            if landkreis in numcaseslookup:
                cases = cases + numcaseslookup[landkreis].numcases
            numcaseslookup[landkreis] = datapoint(
                numcases=cases,
                timestamp=d,
                sourceurl=sourceurl
                )
               
    return numcaseslookup

def eliminateAmbiguousNames(geojsondata):
    allnames = dict()
    for f in geojsondata["features"]:
        p = f["properties"]
        n = p["GEN"]
        if n=="Oldenburg (Oldb)":
            n = "SK Oldenburg"
            p["GEN"] = n
        elif n in allnames and allnames[n]!=p["RS"]:
            if p["BEZ"]=="Landkreis" or p["BEZ"]=="Kreis":
              unambiguousname = "LK " + n
            else:
              unambiguousname = "SK " + n
            p["GEN"] = unambiguousname
        else:
            allnames[p["GEN"]] = p["RS"]

def geojsonprop_caseskey(f, numcaseslookup):
    p = f["properties"]
    try:
        name = p["GEN"]
        try:
            if p["BEZ"]=="Landkreis" or p["BEZ"]=="Kreis":
              name2 = "LK " + name
            else:
              name2 = "SK " + name
            v = numcaseslookup.pop(name2)
            name = name2
        except:            
            v = numcaseslookup.pop(name)
    except:
        name = p["GEN"]
        v = None
    return name,v

numcaseslookup = readNewCSV()
#numcaseslookup = scrapeOfficialNumbers()
processGEOJSON("GERMANY", "RKI_Corona_Landkreise.geojson",
               "county",
               "RS", numcaseslookup,
               lambda f: f["properties"]["EWZ"])

