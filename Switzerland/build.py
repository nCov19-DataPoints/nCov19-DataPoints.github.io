import urllib.request
import csv
from io import StringIO
import json
import datetime
from collections import namedtuple
import sys
sys.path.append('../')
import buildhelpers

numcaseslookup = dict()
lastupdate = ""

def readNewCSV():
    kantonsubst = {
        }
    url="https://github.com/openZH/covid_19/raw/master/COVID19_Cases_Cantons_CH_total.csv"
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('utf-8')

    d = datetime.datetime.now()        
    with StringIO(text) as f:
        csvreader = csv.reader(f, delimiter=',')
        for ncovdatapoint in csvreader:
            name = ncovdatapoint[1].strip();            
            if name == "canton" or name == "" or name == "CH" or name == "FL":
                continue
            d = datetime.datetime.strptime(ncovdatapoint[0], "%Y-%m-%d")
            try:
                name = kantonsubst[name]
            except:
                pass
            if not (name in numcaseslookup) or d>numcaseslookup[name][1]:
                numcaseslookup[name] = [int(ncovdatapoint[2]) if ncovdatapoint[2] != "" else 0, d, "https://github.com/openZH/covid_19/raw/master/COVID19_Cases_Cantons_CH_total.csv"]
        for n in numcaseslookup:
            numcaseslookup[n][1] = numcaseslookup[n][1].strftime(buildhelpers.dateformat)
        with open("ncov19.csv","w") as f:
            f.write("Names,Cases\n")
            for n in numcaseslookup:
                f.write(n+","+str(numcaseslookup[n])+"\n")

readNewCSV()

pop = {
"ZH": 1520968,
"BE": 1034977,
"LU": 409557,
"UR": 36433,
"SZ": 159165,
"OW": 37841,
"NW": 43223,
"GL": 40403,
"ZG": 126837,
"FR": 318714,
"SO": 273194,
"BS": 194766,
"BL": 288132,
"SH": 81991,
"AR": 55234,
"AI": 16145,
"SG": 507697,
"GR": 198379,
"AG": 677387,
"TG": 276472,
"TI": 353343,
"VD": 799145,
"VS": 343955,
"NE": 176850,
"GE": 499480,
"JU": 73419
};

with open("cantons.geojson", "r", encoding="utf-8") as source:
    geojsondata = json.load(source)
    totalCases = 0
    updatetime = datetime.datetime(2020,1,1)
    unmatchedgeojsonnames = []
    for f in geojsondata["features"]:
        p = f["properties"]
        cantonid = f["id"]        
        v = [0, "", ""]
        try:
            v = numcaseslookup.pop(cantonid)
        except:
            unmatchedgeojsonnames.append(cantonid)
        p["NAME"] = p["name"]
        p["ID"] = cantonid
        p["CASES"] = v[0]
        if v[1] != "":
            d = datetime.datetime.strptime(v[1],"%d/%m/%Y %H:%M")
            if updatetime<d:
                updatetime = d
            p["LASTUPDATE"] = d.strftime(buildhelpers.dateformat)
        else:
            p["LASTUPDATE"] = ""      
        p["POPULATION"] = pop[cantonid]
        p["CASESPER10000"] = p["CASES"] / p["POPULATION"] * 10000
        p["SOURCEURL"] = v[2]
        buildhelpers.addstyle(p)
        totalCases = totalCases + p["CASES"]
    if len(numcaseslookup)>0:
        for key in numcaseslookup:
            print("Not found: '"+key+"' ('"+str(key.encode('unicode-escape'))+"') Cases: ",numcaseslookup[key])
        print("GEOJSON contains the following unmatched canton IDs:")
        for n in unmatchedgeojsonnames:
            print("'"+n+"' ('"+str(n.encode('unicode-escape'))+"')")


buildhelpers.generateOutput("SWITZERLAND", geojsondata, totalCases, updatetime)
       
