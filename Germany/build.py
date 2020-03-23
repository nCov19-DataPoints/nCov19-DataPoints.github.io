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
    "StadtRegion Aachen": "Städteregion Aachen",
    "SK Mülheim a.d.Ruhr": "Mülheim an der Ruhr",
    "SK Offenbach": "SK Offenbach am Main",
    "LK Altenkirchen": "LK Altenkirchen (Westerwald)",
    "LK Bitburg-Prüm": "LK Eifelkreis Bitburg-Prüm",
    "SK Landau i.d.Pfalz": "SK Landau in der Pfalz",
    "SK Ludwigshafen": "SK Ludwigshafen am Rhein",
    "SK Neustadt a.d.Weinstraße": "SK Neustadt an der Weinstraße",
    "SK Freiburg i.Breisgau": "SK Freiburg im Breisgau",
    "LK Landsberg a.Lech": "LK Landsberg am Lech",
    "LK Mühldorf a.Inn": "LK Mühldorf a. Inn",
    "LK Pfaffenhofen a.d.Ilm": "LK Pfaffenhofen a.d. Ilm",
    "SK Weiden i.d.OPf.": "SK Weiden i.d. OPf.",
    "LK Neumarkt i.d.OPf.": "LK Neumarkt i.d. OPf.",
    "LK Neustadt a.d.Waldnaab": "LK Neustadt a.d. Waldnaab",
    "LK Wunsiedel i.Fichtelgebirge": "LK Wunsiedel i. Fichtelgebirge",
    "SK Frankenthal": "SK Frankenthal (Pfalz)",
    "LK Neustadt a.d.Aisch-Bad Windsheim": "LK Neustadt a.d. Aisch-Bad Windsheim",
    "LK Dillingen a.d.Donau": "LK Dillingen a.d. Donau",
    "LK Lindau": "LK Lindau (Bodensee)",
    "LK Stadtverband Saarbrücken": "LK Regionalverband Saarbrücken",
    "LK Saar-Pfalz-Kreis": "LK Saarpfalz-Kreis",
    "LK Sankt Wendel": "LK St. Wendel",
    "SK Brandenburg a.d.Havel": "SK Brandenburg an der Havel",
    "SK Halle": "SK Halle (Saale)",
    "SK Berlin Reinickendorf": "SK Berlin",
    "SK Berlin Charlottenburg-Wilmersdorf": "SK Berlin",
    "SK Berlin Treptow-Köpenick": "SK Berlin",
    "SK Berlin Pankow": "SK Berlin",
    "SK Berlin Neukölln": "SK Berlin",
    "SK Berlin Lichtenberg": "SK Berlin",
    "SK Berlin Marzahn-Hellersdorf": "SK Berlin",
    "SK Berlin Spandau": "SK Berlin",
    "SK Berlin Steglitz-Zehlendorf": "SK Berlin",
    "SK Berlin Mitte": "SK Berlin",
    "SK Berlin Friedrichshain-Kreuzberg": "SK Berlin",
    "SK Berlin Tempelhof-Schöneberg": "SK Berlin",
    "LK Kassel": "Region Kassel",
    "SK Kassel": "Region Kassel"
    }

def readNewCSV():
    numcaseslookup = dict()

    url="https://opendata.arcgis.com/datasets/917fc37a709542548cc3be077a786c17_0.csv"
    sourceurl="https://npgeo-corona-npgeo-de.hub.arcgis.com/datasets/917fc37a709542548cc3be077a786c17_0/data"
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('utf-8')

    d = datetime.datetime.now(tz=CET)
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
            if landkreis=="LK Oberallgäu":
                # Oberallgäu und Stadt Kempten sind nicht getrennt in der Statistik
                # Einwohner Oberallgäu: 155362, Kempten: 68907
                # Die Fälle für Oberallgäu entsprechend aufteilen
                numCases = int(ncovdatapoint[29]) if (ncovdatapoint[29] != "" and ncovdatapoint[29] != "-") else 0
                numCasesOberallgaeu = int(numCases * 155362.0 / (68907.0 + 155362.0))
                numCasesKempten = numCases - numCasesOberallgaeu
                numcaseslookup["SK Kempten (Allgäu)"] = datapoint(
                    numcases=numCasesKempten,
                    timestamp=d,
                    sourceurl=sourceurl
                    )
                numcaseslookup["LK Oberallgäu"] = datapoint(
                    numcases=numCasesOberallgaeu,
                    timestamp=d,
                    sourceurl=sourceurl
                )
            else:
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
processGEOJSON("GERMANY", "landkreise_simplify200_simplified.geojson",
               geojsonprop_caseskey,
               "RS", numcaseslookup,
               lambda f: f["properties"]["destatis"]["population"],
               eliminateAmbiguousNames)

