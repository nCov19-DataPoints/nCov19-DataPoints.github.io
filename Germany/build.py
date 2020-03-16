import urllib.request
import csv
from io import StringIO
import json
import datetime
from collections import namedtuple
import sys
sys.path.append('../')
import buildhelpers
import re
import locale
from bs4 import BeautifulSoup

numcaseslookup = dict()
lastupdate = ""

landkreissubst = {
    "Aachen & Städteregion Aachen": "Städteregion Aachen",
    "Mülheim / Ruhr": "Mülheim an der Ruhr",
    "Nienburg": "Nienburg (Weser)",
    "Rotenburg": "Rotenburg (Wümme)",
    
    "Frankfurt": "Frankfurt am Main",
    "Offenbach (Landkreis)": "Offenbach", 
    "Offenbach (Stadt)": "Offenbach am Main",
    "Region Kassel": "Kassel Landkreis",
    "Landeshauptstadt Dresden": "Dresden",
    "Pfaffenhofen a.d.Ilm": "Pfaffenhofen a.d. Ilm",
    "Neumarkt i.d.Opf.": "Neumarkt i.d. OPf.",
    "Saarpfalz": "Saarpfalz-Kreis",
    "Weiden Stadt": "Weiden i.d. OPf.",
    "Brandenburg a. d. Havel": "Brandenburg an der Havel",
    "Bad Tölz": "Bad Tölz-Wolfratshausen",
    "Halle": "Halle (Saale)"
    }

def readNewCSV():
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
            numcaseslookup[landkreis] = [int(ncovdatapoint[2]) if (ncovdatapoint[2] != "" and ncovdatapoint[2] != "-") else 0, ncovdatapoint[4], ncovdatapoint[3]]
        with open("ncov19.csv","w") as f:
            f.write("Names,Cases\n")
            for n in numcaseslookup:
                pn = n.replace(" (district)", "")
                f.write(pn+","+str(numcaseslookup[n])+"\n")

def parseDateTimeWithLocale(datetext, dateformat, datelocale):
  lc = locale.setlocale(locale.LC_TIME)
  try:
    locale.setlocale(locale.LC_TIME, datelocale)
    return datetime.datetime.strptime(datetext, dateformat)
  finally:
    locale.setlocale(locale.LC_TIME, lc)
    
def scrapeOfficialNumbers():
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
    
    with open("ncov19.csv","w") as f:
        f.write("Names,Cases\n")
        for n in numcaseslookup:
            pn = n.replace(" (district)", "")
            f.write(pn+","+str(numcaseslookup[n])+"\n")    

readNewCSV()
#scrapeOfficialNumbers()

with open("landkreise_simplify200_simplified.geojson", "r", encoding="utf-8") as source:
    geojsondata = json.load(source)
    totalCases = 0
    updatetime = datetime.datetime(2020,1,1)
    unmatchedgeojsonnames = []
    for f in geojsondata["features"]:
        p = f["properties"]
        name = p["GEN"]        
        if p["BEZ"]=="Landkreis" or p["BEZ"]=="Kreis":
          name = name + " Landkreis"        
        else:
          name = name + " Stadt"
        v = [0, "", ""]
        try:
            v = numcaseslookup.pop(name)
        except:
            try:
                origname = p["GEN"]
                v = numcaseslookup.pop(origname)
                name = origname
            except:
                unmatchedgeojsonnames.append(name)
        p["NAME"] = name
        p["ID"] = p["RS"]
        p["CASES"] = v[0]
        if v[1] != "":
            d = datetime.datetime.strptime(v[1],"%d/%m/%Y %H:%M")
            if updatetime<d:
                updatetime = d
            p["LASTUPDATE"] = d.strftime(buildhelpers.dateformat)
        else:
            p["LASTUPDATE"] = ""
        p["POPULATION"] = p["destatis"]["population"]
        p["CASESPER10000"] = p["CASES"] / p["POPULATION"] * 10000
        p["SOURCEURL"] = v[2]
        buildhelpers.addstyle(p)
        totalCases = totalCases + p["CASES"]
    if len(numcaseslookup)>0:
        for key in numcaseslookup:
            print("Not found: '"+key+"' ('"+str(key.encode('unicode-escape'))+"') Cases: ",numcaseslookup[key])
        print("GEOJSON contains the following unmatched names:")
        for n in unmatchedgeojsonnames:
            print("'"+n+"' ('"+str(n.encode('unicode-escape'))+"')")
            
buildhelpers.generateOutput("GERMANY", geojsondata, totalCases, updatetime)
