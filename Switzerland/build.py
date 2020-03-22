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

mapidtoname = {
    'ZH': 'Zürich',
    'BE': 'Bern/Berne',
    'LU': 'Luzern',
    'UR': 'Uri',
    'SZ': 'Schwyz',
    'OW': 'Obwalden',
    'NW': 'Nidwalden',
    'GL': 'Glarus',
    'ZG': 'Zug',
    'FR': 'Fribourg',
    'SO': 'Solothurn',
    'BS': 'Basel-Stadt',
    'BL': 'Basel-Landschaft',
    'SH': 'Schaffhausen',
    'AR': 'Appenzell Ausserrhoden',
    'AI': 'Appenzell Innerrhoden',
    'SG': 'St. Gallen',
    'GR': 'Graubünden/Grigioni',
    'AG': 'Aargau',
    'TG': 'Thurgau',
    'TI': 'Ticino',
    'VD': 'Vaud',
    'VS': 'Valais/Wallis',
    'NE': 'Neuchâtel',
    'GE': 'Genève',
    'JU': 'Jura'
}

pop = {
    "Zürich": 1520968,
    "Bern/Berne": 1034977,
    "Luzern": 409557,
    "Uri": 36433,
    "Schwyz": 159165,
    "Obwalden": 37841,
    "Nidwalden": 43223,
    "Glarus": 40403,
    "Zug": 126837,
    "Fribourg": 318714,
    "Solothurn": 273194,
    "Basel-Stadt": 194766,
    "Basel-Landschaft": 288132,
    "Schaffhausen": 81991,
    "Appenzell Ausserrhoden": 55234,
    "Appenzell Innerrhoden": 16145,
    "St. Gallen": 507697,
    "Graubünden/Grigioni": 198379,
    "Aargau": 677387,
    "Thurgau": 276472,
    "Ticino": 353343,
    "Vaud": 799145,
    "Valais/Wallis": 343955,
    "Neuchâtel": 176850,
    "Genève": 499480,
    "Jura": 73419
};

CET = pytz.timezone('CET')

def readNewCSV(filename, cantonidcolumn, casecolumn):
    numcaseslookup = dict()
    kantonsubst = {
        }
    url="https://github.com/openZH/covid_19/raw/master/fallzahlen_kanton_total_csv/" + filename
    try:
        response = urllib.request.urlopen(url)
    except:
        print("Failed to open URL '" + url + "' for Swiss data")
        return numcaseslookup
    data = response.read()
    text = data.decode('utf-8')    

    with StringIO(text) as f:
        csvreader = csv.reader(f, delimiter=',')
        for ncovdatapoint in csvreader:
            cantonid = ncovdatapoint[cantonidcolumn].strip();            
            if cantonid in ["abbreviation_canton_and_fl","canton" ,"","CH","FL"]:
                continue
            name = mapidtoname[cantonid]
            try:
                if len(ncovdatapoint[1])>0:
                    d = CET.localize(datetime.datetime.strptime(ncovdatapoint[0] + " " + ncovdatapoint[1], "%Y-%m-%d %H:%M"))
                else:
                    d = CET.localize(datetime.datetime.strptime(ncovdatapoint[0] , "%Y-%m-%d"))
            except:
                print("Column 0=Date='" + ncovdatapoint[0] + "' + Column 1=Time='" + ncovdatapoint[1] +"' does not match datetime format")
            try:
                name = kantonsubst[name]
            except:
                pass
            if not (name in numcaseslookup) or d>numcaseslookup[name].timestamp:
                numcaseslookup[name] = datapoint(
                    numcases=int(ncovdatapoint[casecolumn]) if ncovdatapoint[casecolumn] != "" else 0,
                    timestamp=d,
                    sourceurl="https://github.com/openZH/covid_19/blob/master/fallzahlen_kanton_total_csv/"+filename
                    )

    return numcaseslookup

numcaseslookup = {}
for id in mapidtoname:
    numcaseslookup = { **numcaseslookup, **readNewCSV("COVID19_Fallzahlen_Kanton_" + id + "_total.csv", 2, 4) }

processGEOJSON("SWITZERLAND", "cantons.geojson", "name", lambda f: f["id"], numcaseslookup, pop)

