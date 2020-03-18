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
    'JU': 'Jura',
    'Canton_ZH': 'Zürich',
    'Canton_TG': 'Thurgau',
    'Canton_BE': 'Bern/Berne',
    'Canton_BS': 'Basel-Stadt'
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

def readNewCSV(filename, dateformat, datecolumn, cantonidcolumn, casecolumn):
    numcaseslookup = dict()
    kantonsubst = {
        }
    url="https://github.com/openZH/covid_19/raw/master/" + filename
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('utf-8')    

    with StringIO(text) as f:
        csvreader = csv.reader(f, delimiter=',')
        for ncovdatapoint in csvreader:
            cantonid = ncovdatapoint[cantonidcolumn].strip();            
            if cantonid in ["Area","canton" ,"","CH","FL"]:                
                continue
            name = mapidtoname[cantonid]
            d = CET.localize(datetime.datetime.strptime(ncovdatapoint[datecolumn], dateformat))
            try:
                name = kantonsubst[name]
            except:
                pass
            if not (name in numcaseslookup) or d>numcaseslookup[name].timestamp:
                numcaseslookup[name] = datapoint(
                    numcases=int(ncovdatapoint[casecolumn]) if ncovdatapoint[casecolumn] != "" else 0,
                    timestamp=d,
                    sourceurl="https://github.com/openZH/covid_19/blob/master/"+filename
                    )

    return numcaseslookup

numcaseslookup = readNewCSV("COVID19_Cases_Cantons_CH_total.csv", "%Y-%m-%d", 0, 1, 2)
numcaseslookup = { **numcaseslookup, **readNewCSV("COVID19_Fallzahlen_Kanton_ZH_total.csv", "%d.%m.%Y", 0, 1, 3) }
numcaseslookup = { **numcaseslookup, **readNewCSV("COVID19_Fallzahlen_Kanton_TG_total.csv", "%d.%m.%Y", 0, 1, 3) }
numcaseslookup = { **numcaseslookup, **readNewCSV("COVID19_Fallzahlen_Kanton_BE_total.csv", "%d.%m.%Y", 0, 1, 3) }
numcaseslookup = { **numcaseslookup, **readNewCSV("COVID19_Fallzahlen_Kanton_BS_total.csv", "%d.%m.%Y", 0, 1, 3) }

processGEOJSON("SWITZERLAND", "cantons.geojson", "name", lambda f: f["id"], numcaseslookup, pop)

