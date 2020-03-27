import urllib.request
import csv
from io import StringIO
import json
import datetime
import pytz
from collections import namedtuple

CET = pytz.timezone('CET')

Color = namedtuple("Color",['r','g','b','a'])
colortable = [
     {"t":0, "c":{"r":0,"g":255,"b":0,"a":0.1} },
     {"t":0.1, "c":{"r":128,"g":255,"b":0,"a":0.1} },
     {"t":0.25, "c":{"r":255,"g":255,"b":0,"a":0.1} },
     {"t":0.5, "c":{"r":255,"g":213,"b":0,"a":0.2} },
     {"t":1.0, "c":{"r":255,"g":191,"b":0,"a":0.3} },
     {"t":2.5, "c":{"r":255,"g":128,"b":0,"a":0.3} },
     {"t":5.0, "c":{"r":255,"g":0,"b":0,"a":0.3} },
     {"t":10.0, "c":{"r":255,"g":0,"b":0,"a":0.4} },
     {"t":25.0, "c":{"r":255,"g":0,"b":0,"a":0.5} },
     {"t":50.0, "c":{"r":255,"g":0,"b":64,"a":0.5} },
     {"t":75.0, "c":{"r":255,"g":0,"b":128,"a":0.5} },
     {"t":100.0, "c":{"r":255,"g":0,"b":191,"a":0.5} }
    ]
colortableoutdated = [
    {"t": 0, "c": {"r": 102, "g": 153, "b": 102, "a": 0.1}},
    {"t": 0.1, "c": {"r": 128, "g": 153, "b": 102, "a": 0.1}},
    {"t": 0.25, "c": {"r": 153, "g": 153, "b": 102, "a": 0.1}},
    {"t": 0.5, "c": {"r": 153, "g": 145, "b": 102, "a": 0.2}},
    {"t": 1.0, "c": {"r": 153, "g": 140, "b": 102, "a": 0.3}},
    {"t": 2.5, "c": {"r": 153, "g": 128, "b": 102, "a": 0.3}},
    {"t": 5.0, "c": {"r": 153, "g": 102, "b": 102, "a": 0.3}},
    {"t": 10.0, "c": {"r": 153, "g": 102, "b": 102, "a": 0.4}},
    {"t": 25.0, "c": {"r": 153, "g": 102, "b": 102, "a": 0.5}},
    {"t": 50.0, "c": {"r": 153, "g": 102, "b": 128, "a": 0.5}},
    {"t": 75.0, "c": {"r": 153, "g": 102, "b": 141, "a": 0.5}},
    {"t": 100.0, "c": {"r": 153, "g": 102, "b": 153, "a": 0.5}}
]


def calculateColor(colortable,v):
    indexge = len(colortable)
    for i in range(0,len(colortable)):
        if v<=colortable[i]["t"]:
            indexge = i;
            break;
    tl = colortable[max(0,indexge-1)]
    th = colortable[min(indexge,len(colortable)-1)]
    l = tl["c"]
    h = th["c"]
    #fl = (v - tl["t"])/(th["t"] - tl["t"]) if th["t"]>tl["t"] else 1.0
    fl = 1.0
    fh = 1.0 - fl
    return Color(
        int(fl*l["r"]+fh*h["r"]),
        int(fl*l["g"]+fh*h["g"]),
        int(fl*l["b"]+fh*h["b"]),
        fl*l["a"]+fh*h["a"]
        )
      
class datapoint:
    def __init__(self, numcases, timestamp, sourceurl):
        self.numcases = numcases
        self.timestamp = timestamp
        self.sourceurl = sourceurl

    def __str__(self):
        return "datapoint(numcases="+str(self.numcases)+",timestamp="+self.timestamp.isoformat()+",sourceurl='"+self.sourceurl+"'"
        
def processGEOJSON(country, geojsonfilename, geojsonprop_caseskey, geojsonprop_id, numcaseslookup, populationlookup, preprocessgeojson = None):
    totalCases = 0
    mostrecentupdate = max(numcaseslookup[n].timestamp for n in numcaseslookup)

    with open("ncov19.csv","w") as f:
        f.write("Names,Cases\n")
        for n in numcaseslookup:
            f.write(n + "," + str(numcaseslookup[n].numcases) + "," + numcaseslookup[n].timestamp.isoformat() + "," + numcaseslookup[n].sourceurl+"\n")

    with open(geojsonfilename, "r", encoding="utf-8") as source:
        geojsondata = json.load(source)
                
        if preprocessgeojson:
           preprocessgeojson(geojsondata)
        unmatchedgeojsonnames = []
        for f in geojsondata["features"]:
            p = f["properties"]
            if isinstance(geojsonprop_caseskey, str):
                name = p[geojsonprop_caseskey]    
                try:
                    v = numcaseslookup.pop(name)
                except:
                    v = None
            else:
                try:
                    name, v = geojsonprop_caseskey(f, numcaseslookup)
                except:
                    name, v = "???", None
            if v==None:
                v = datapoint(numcases = 0, timestamp = mostrecentupdate, sourceurl = "")
                unmatchedgeojsonnames.append(name)
            p["NAME"] = name
            p["ID"] = p[geojsonprop_id] if isinstance(geojsonprop_id, str) else geojsonprop_id(f)
            p["CASES"] = v.numcases
            p["LASTUPDATE"] = v.timestamp.isoformat()
            p["POPULATION"] = populationlookup[name] if isinstance(populationlookup, dict) else populationlookup(f)
            p["CASESPER10000"] = p["CASES"] / p["POPULATION"] * 10000
            p["SOURCEURL"] = v.sourceurl
            colors = colortable if v.timestamp + datetime.timedelta(hours=96) > datetime.datetime.now(datetime.timezone.utc) else colortableoutdated
            fillColor = calculateColor(colors,p["CASESPER10000"])
            p["fill"] = True
            p["fillColor"] = "#{0:02x}{1:02x}{2:02x}".format(fillColor.r,fillColor.g,fillColor.b)
            p["fillOpacity"] = fillColor.a
            p["weight"] = 1
            p["opacity"] = 0.3
            totalCases = totalCases + p["CASES"]
        if len(numcaseslookup)>0:
            for key in numcaseslookup:
                print("Not found: '"+key+"' ('"+str(key.encode('unicode-escape'))+"') Datapoint: ",numcaseslookup[key])
            print("GEOJSON contains the following unmatched names:")
            for n in unmatchedgeojsonnames:
                print("'"+n+"' ('"+str(n.encode('unicode-escape'))+"')")
        
    print(country+": assigned "+str(totalCases)+" cases to geojson features.")

    with open("ncov19map.geojson", "w") as dest:
        json.dump(geojsondata,dest)
    
    with open("ncov19map.js", "w") as dest:
        dest.write("GEOJSON_" + country + "=")
        json.dump(geojsondata,dest)
        dest.write(";")
        dest.write("\nGEOJSON_totalCases=GEOJSON_totalCases+"+str(totalCases))
        dest.write("\nGEOJSON_lastoverallupdate=new Date(Math.max("+str((mostrecentupdate - datetime.datetime(1970,1,1, tzinfo=datetime.timezone.utc)).total_seconds()*1000)+",GEOJSON_lastoverallupdate.valueOf()));")
        now = datetime.datetime.utcnow()
        dest.write("\nGEOJSON_lastbuildrunutc=new Date(Math.max(Date.UTC("+str(now.year)+","+str(now.month-1)+","+str(now.day)+","+str(now.hour)+","+str(now.minute)+","+str(now.second)+"),GEOJSON_lastbuildrunutc));")
        dest.write("\nlegendColors=[")
        for i in range(0,len(colortable)):
            dest.write("\n  {{ v:{0},c:\"#{1:02x}{2:02x}{3:02x}\",o:{4} }}".format(colortable[i]["t"],colortable[i]["c"]["r"],colortable[i]["c"]["g"],colortable[i]["c"]["b"],colortable[i]["c"]["a"]))
            if i!=len(colortable)-1:
                dest.write(",")
        dest.write("\n];")
    print("Completed exporting "+country)


