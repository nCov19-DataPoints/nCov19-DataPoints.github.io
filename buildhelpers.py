import urllib.request
import csv
from io import StringIO
import json
import datetime
from collections import namedtuple

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
     {"t":100.0, "c":{"r":255,"g":0,"b":128,"a":0.5} }
    ]
def calculateColor(v):
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

def generateOutput(country, geojsondata, totalCases, updatetime):
    print(country+": assigned "+str(totalCases)+" cases to geojson features.")

    with open("ncov19map.geojson", "w") as dest:
        json.dump(geojsondata,dest)
    
    with open("ncov19map.js", "w") as dest:
        dest.write("GEOJSON_" + country + "=")
        json.dump(geojsondata,dest)
        dest.write(";")
        dest.write("\nGEOJSON_totalCases=GEOJSON_totalCases+"+str(totalCases))
        dest.write("\nGEOJSON_lastoverallupdate=new Date(Math.max("+str((updatetime - datetime.datetime(1970,1,1)).total_seconds()*1000)+",GEOJSON_lastoverallupdate.valueOf()));")
        dest.write("\nlegendColors=[")
        for i in range(0,len(colortable)):
            dest.write("\n  {{ v:{0},c:\"#{1:02x}{2:02x}{3:02x}\",o:{4} }}".format(colortable[i]["t"],colortable[i]["c"]["r"],colortable[i]["c"]["g"],colortable[i]["c"]["b"],colortable[i]["c"]["a"]))
            if i!=len(colortable)-1:
                dest.write(",")
        dest.write("\n];")
    print("Completed exporting "+country)


def addstyle(p):
    fillColor = calculateColor(p["CASESPER10000"])
    p["fill"] = True
    p["fillColor"] = "#{0:02x}{1:02x}{2:02x}".format(fillColor.r,fillColor.g,fillColor.b)
    p["fillOpacity"] = fillColor.a
    p["weight"] = 1
    p["opacity"] = 0.3
    
dateformat = "%d/%m/%Y %H:%M"
