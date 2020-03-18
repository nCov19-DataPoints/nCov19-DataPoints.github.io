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
    "Aachen & Städteregion Aachen": "Städteregion Aachen",
    "Mülheim / Ruhr": "Mülheim an der Ruhr",
    "Nienburg": "Nienburg (Weser)",
    "Rotenburg": "Rotenburg (Wümme)",
    "Wunsiedel i.Fichtelgebirge": "Wunsiedel i. Fichtelgebirge",
    "Oldenburg": "Oldenburg Stadt",
    "Aschaffenburg": "Aschaffenburg Landkreis",
    "Augsburg": "Augsburg Landkreis",
    "Bamberg": "Bamberg Landkreis",
    "Fürth": "Fürth Landkreis",
    "Hof": "Hof Landkreis",
    "Landshut": "Landshut Landkreis",
    "München": "München Landkreis",
    "Passau": "Passau Landkreis",
    "Regensburg": "Regensburg Landkreis",
    "Würzburg": "Würzburg Landkreis",
    "Kaiserslautern": "Kaiserslautern Landkreis",
    "Heilbronn": "Heilbronn Landkreis",
    "Karlsruhe": "Karlsruhe Landkreis",
    "Mühldorf a.Inn": "Mühldorf a. Inn",
    "Rosenheim": "Rosenheim Landkreis",

    "Frankfurt": "Frankfurt am Main",
    "Offenbach (Landkreis)": "Offenbach", 
    "Offenbach (Stadt)": "Offenbach am Main",
    "Landeshauptstadt Dresden": "Dresden",
    "Pfaffenhofen a.d.Ilm": "Pfaffenhofen a.d. Ilm",
    "Neumarkt i.d.Opf.": "Neumarkt i.d. OPf.",
    "Saarpfalz": "Saarpfalz-Kreis",
    "Weiden Stadt": "Weiden i.d. OPf.",
    "Brandenburg a. d. Havel": "Brandenburg an der Havel",
    "Bad Tölz": "Bad Tölz-Wolfratshausen",
    "Halle": "Halle (Saale)",
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
            landkreis = landkreis.replace(" (Stadt)"," Stadt")
            landkreis = landkreis.replace(" (Land)"," Landkreis")
            landkreis = landkreis.replace(" (Kreis)"," Landkreis")
            if landkreis.startswith("Landkreis "):
                landkreis = landkreis.replace("Landkreis ","") + " Landkreis"
            if landkreis.startswith("Stadt "):
                landkreis = landkreis.replace("Stadt ","") + " Stadt"
            landkreis = landkreis.replace(" (kreisfreie Stadt)"," Stadt")
            landkreis = landkreis.replace(" (Stadtkreis)"," Stadt")
            d = CET.localize(datetime.datetime.strptime(ncovdatapoint[4], "%d/%m/%Y %H:%M"))
            numcaseslookup[landkreis] = datapoint(
                numcases=int(ncovdatapoint[2]) if (ncovdatapoint[2] != "" and ncovdatapoint[2] != "-") else 0,
                timestamp=d,
                sourceurl=ncovdatapoint[3]
                )
               
    return numcaseslookup

def parseDateTimeWithLocale(datetext, dateformat, datelocale):
  lc = locale.setlocale(locale.LC_TIME)
  try:
    locale.setlocale(locale.LC_TIME, datelocale)
    return datetime.datetime.strptime(datetext, dateformat)
  finally:
    locale.setlocale(locale.LC_TIME, lc)
    
def scrapeOfficialNumbers():
    numcaseslookup = dict()
    url="http://www.mags.nrw/coronavirus-fallzahlen-nrw"
    response = urllib.request.urlopen(url)
    urldata = response.read()
    html_doc = urldata.decode('utf-8')
    soup = BeautifulSoup(html_doc, 'html.parser')

    dateregex = re.compile(".*Aktueller Stand der Liste: (.*) Uhr")
    blabla = soup.find("p",string=dateregex)
    datematch = dateregex.match(blabla.text)
    datetext = datematch.group(1)
    lastupdate = parseDateTimeWithLocale(datetext, "%d. %B %Y, %H.%M", "de_DE")
    datetext = lastupdate.strftime("%d/%m/%Y %H:%M")
    
    th = soup.find('th', string='Bestätigte Fälle')
    table_body = th.parent.parent.parent.find('tbody')

    rows = table_body.find_all('tr')
    if len(rows)!=54:
        print("Expecting 54 rows in '"+url+"' but found "+str(len(rows))+" rows instead. Rows:\n"+str(rows))
        
    for row in rows:
        cols = row.find_all('td')
        if len(cols)!=2:
            print("Expecting 2 columns in row '"+str(row)+"' scraped from '"+url+"' but found "+str(len(cols))+" columns instead.")

        landkreis = cols[0].text.strip()
        if landkreis=="Gesamt":
            continue       
        try:
            landkreis = landkreissubst[landkreis]
        except:
            pass
        landkreis = landkreis.replace(" (Stadt)"," Stadt")
        landkreis = landkreis.replace(" (Land)"," Landkreis")
        if landkreis.startswith("Landkreis "):
            landkreis = landkreis.replace("Landkreis ","") + " Landkreis"
        if landkreis.startswith("Stadt "):
            landkreis = landkreis.replace("Stadt ","") + " Stadt"
        landkreis = landkreis.replace(" (kreisfreie Stadt)"," Stadt")
        landkreis = landkreis.replace(" (Stadtkreis)"," Stadt")
        
        faelle = cols[1].text.strip()        
        
        numcaseslookup[landkreis] = [int(faelle) if (faelle != "" and faelle != "-") else 0, datetext, url]        

    print(numcaseslookup)

    return numcaseslookup

def eliminateAmbiguousNames(geojsondata):
    allnames = dict()
    for f in geojsondata["features"]:
        p = f["properties"]
        n = p["GEN"]
        if n=="Oldenburg (Oldb)":
            n = "Oldenburg Stadt"
            p["GEN"] = n
        elif n in allnames and allnames[n]!=p["RS"]:
            if p["BEZ"]=="Landkreis" or p["BEZ"]=="Kreis":
              unambiguousname = n + " Landkreis"        
            else:
              unambiguousname = n + " Stadt"        
            p["GEN"] = unambiguousname
        else:
            allnames[p["GEN"]] = p["RS"]

def geojsonprop_caseskey(f, numcaseslookup):
    p = f["properties"]
    try:
        name = p["GEN"]
        try:
            if p["BEZ"]=="Landkreis" or p["BEZ"]=="Kreis":
              name2 = name + " Landkreis"        
            else:
              name2 = name + " Stadt"        
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

