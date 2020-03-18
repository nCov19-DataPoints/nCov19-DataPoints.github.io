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
    "SK Freiburg i.Breisgau": 'SK Freiburg im Breisgau',
    'LK Neustadt/Aisch-Bad Windsheim': 'LK Neustadt a.d. Aisch-Bad Windsheim',
    'LK Landsberg a.Lech': 'LK Landsberg am Lech',
    'LK Mühldorf a.Inn': 'LK Mühldorf a. Inn',
    'LK Pfaffenhofen a.d.Ilm': 'LK Pfaffenhofen a.d. Ilm',
    'LK Wunsiedel i.Fichtelgebirge': 'LK Wunsiedel i. Fichtelgebirge',
    'LK Neumarkt i.d.OPf.': 'LK Neumarkt i.d. OPf.',
    'LK Neustadt a.d.Waldnaab': 'LK Neustadt a.d. Waldnaab',
    'SK Weiden i.d.OPf.': 'SK Weiden i.d. OPf.',
    'LK Dillingen a.d.Donau': 'LK Dillingen a.d. Donau',
    'SK Kempten':'SK Kempten (Allgäu)',
    'LK Lindau':'LK Lindau (Bodensee)',
    'SK Berlin Charlottenburg-Wilmersdorf':'SK Berlin',
    'SK Berlin Friedrichshain-Kreuzberg':'SK Berlin',
    'SK Berlin Lichtenberg':'SK Berlin',
    'SK Berlin Marzahn-Hellersdorf':'SK Berlin',
    'SK Berlin Mitte':'SK Berlin',
    'SK Berlin Neukölln':'SK Berlin',
    'SK Berlin Pankow':'SK Berlin',
    'SK Berlin Reinickendorf':'SK Berlin',
    'SK Berlin Spandau':'SK Berlin',
    'SK Berlin Steglitz-Zehlendorf':'SK Berlin',
    'SK Berlin Tempelhof-Schöneberg':'SK Berlin',
    'SK Berlin Treptow-Köpenick':'SK Berlin',
    'SK Brandenburg a.d.Havel':'SK Brandenburg an der Havel',
    'SK Offenbach':'SK Offenbach am Main',
    'SK Oldenburg':'SK Oldenburg (Oldb)',
    'SK Mülheim a.d.Ruhr':'SK Mülheim an der Ruhr',
    'LK Altenkirchen':'LK Altenkirchen (Westerwald)',
    'SK Frankenthal':'SK Frankenthal (Pfalz)',
    'SK Landau i.d.Pfalz':'SK Landau in der Pfalz',
    'SK Ludwigshafen':'SK Ludwigshafen am Rhein',
    'SK Neustadt a.d.Weinstraße':'SK Neustadt an der Weinstraße',
    'LK Bitburg-Prüm':'LK Eifelkreis Bitburg-Prüm',
    'LK Saar-Pfalz-Kreis':'LK Saarpfalz-Kreis',
    'LK Sankt Wendel':'LK St. Wendel',
    'LK Stadtverband Saarbrücken':'LK Regionalverband Saarbrücken',
    'SK Halle':'SK Halle (Saale)',
    'LK Ludwigslust–Parchim':'LK Ludwigslust-Parchim',
    'LK Vorpommern–Greifswald':'LK Vorpommern-Greifswald',
    'LK Vorpommern–Rügen':'LK Vorpommern-Rügen',
    'StädteRegion Aachen':'Städteregion Aachen'
}

def readNewCSV():
    numcaseslookup = dict()

    url="https://script.google.com/macros/s/AKfycbwGDICHD1yhtgqXelmnAvsobEqxYuTpZVBxow8x0HA9x34eoDnv/exec"
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('utf-8')

    with StringIO(text) as f:
        csvreader = csv.reader(f, delimiter=',')
        for ncovdatapoint in csvreader:
            land = ncovdatapoint[0].strip();
            if land == "Bundesland" or land == "":
                continue
            landkreis = ncovdatapoint[1].strip();            
            try:
                landkreis = landkreissubst[landkreis]
            except:
                pass            
            d = CET.localize(datetime.datetime.strptime(ncovdatapoint[4], "%d/%m/%Y %H:%M"))
            if landkreis in numcaseslookup:
                # Special case for Berlin for now
                numcaseslookup[landkreis].numcases = numcaseslookup[landkreis].numcases + int(ncovdatapoint[2]) if (ncovdatapoint[2] != "" and ncovdatapoint[2] != "-") else 0
            else:
                numcaseslookup[landkreis] = datapoint(
                    numcases=int(ncovdatapoint[2]) if (ncovdatapoint[2] != "" and ncovdatapoint[2] != "-") else 0,
                    timestamp=d,
                    sourceurl=ncovdatapoint[3]
                    )
               
    return numcaseslookup

def eliminateAmbiguousNames(geojsondata):
    for f in geojsondata["features"]:
        p = f["properties"]
        n = p["GEN"]
        if not (n.startswith("Region ") or n.startswith("Städteregion ")):
            if p["BEZ"]=="Landkreis" or p["BEZ"]=="Kreis":
              p["GEN"] = "LK " + n
            else:
              p["GEN"] = "SK " + n

numcaseslookup = readNewCSV()
processGEOJSON("GERMANY", "landkreise_simplify200.geojson",
               "GEN",
               "RS", numcaseslookup,
               lambda f: f["properties"]["destatis"]["population"],
               eliminateAmbiguousNames)

