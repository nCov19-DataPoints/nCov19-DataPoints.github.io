import urllib.request
import csv
from io import StringIO
import json
import datetime
import pytz
from collections import namedtuple
import sys
sys.path.append('../')
import buildhelpers

italypop = {
    "Agrigento":438276,
    "Alessandria":424174,
    "Ancona":472603,
    "Valle d'Aosta/Vallée d'Aoste":126202,
    "Arezzo":343449,
    "Ascoli Piceno":208377,
    "Asti":215884,
    "Avellino":439137,
    "Bari":1258706,
    "Barletta-Andria-Trani":392863,
    "Belluno":213474,
    "Benevento":287874,
    "Bergamo":1098740,
    "Biella":185768,
    "Bologna":991924,
    "Brescia":1256025,
    "Brindisi":403229,
    "Cagliari":430413,
    "Caltanissetta":271729,
    "Campobasso":231086,
    "Caserta":916467,
    "Catania":1090101,
    "Catanzaro":368597,
    "Chieti":397123,
    "Como":594988,
    "Cosenza":734656,
    "Cremona":363606,
    "Crotone":174605,
    "Cuneo":592303,
    "Enna":172485,
    "Fermo":177914,
    "Ferrara":359994,
    "Firenze":998098,
    "Foggia":640836,
    "Forlì-Cesena":395489,
    "Frosinone":498167,
    "Genova":882718,
    "Gorizia":142407,
    "Grosseto":228157,
    "Imperia":222648,
    "Isernia":88694,
    "La Spezia":223516,
    "L'Aquila":309820,
    "Latina":555692,
    "Lecce":815597,
    "Lecco":340167,
    "Livorno":342955,
    "Lodi":227655,
    "Lucca":393795,
    "Macerata":325362,
    "Mantova":415442,
    "Massa-Carrara":203901,
    "Matera":203726,
    "Messina":653737,
    "Milano":3156694,
    "Modena":700913,
    "Monza e della Brianza":849636,
    "Napoli":3080873,
    "Novara":371802,
    "Nuoro":210972,
    "Oristano":159474,
    "Padova":934216,
    "Palermo":1249577,
    "Parma":442120,
    "Pavia":548307,
    "Perugia":671821,
    "Pesaro e Urbino":366963,
    "Pescara":323184,
    "Piacenza":289875,
    "Pisa":417782,
    "Pistoia":293061,
    "Pordenone":315323,
    "Potenza":383791,
    "Prato":249775,
    "Ragusa":318549,
    "Ravenna":392458,
    "Reggio di Calabria":566977,
    "Reggio nell'Emilia":530343,
    "Rieti":160467,
    "Rimini":329302,
    "Roma":4194068,
    "Rovigo":247884,
    "Salerno":1109705,
    "Sassari":493357,
    "Savona":287906,
    "Siena":272638,
    "Sondrio":183169,
    "Sud Sardegna":354553,
    "Bolzano/Bozen":507657,
    "Siracusa":404271,
    "Taranto":580028,
    "Teramo":312239,
    "Terni":234665,
    "Trapani":436624,
    "Trento":529457,
    "Treviso":888249,
    "Trieste":236556,
    "Torino":2302353,
    "Udine":541522,
    "Varese":883285,
    "Venezia":863133,
    "Verbano-Cusio-Ossola":163247,
    "Vercelli":179562,
    "Verona":920158,
    "Vibo Valentia":166560,
    "Vicenza":870740,
    "Viterbo":320294
}

CET = pytz.timezone('CET')

def readNewCSV():
    namesubst = {
        "Bolzano": "Bolzano/Bozen",
        "ForlÃ¬-Cesena": "Forlì-Cesena",
        "Massa Carrara": "Massa-Carrara",
        "Aosta": "Valle d'Aosta/Vallée d'Aoste"
        }
    url="https://github.com/pcm-dpc/COVID-19/raw/master/dati-province/dpc-covid19-ita-province.csv"
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('utf-8')

    numcaseslookup = dict()
    with StringIO(text) as f:
        csvreader = csv.reader(f, delimiter=',')
        for ncovdatapoint in csvreader:
            name = ncovdatapoint[5].strip();            
            if name == "denominazione_provincia" or name == "" or name == "In fase di definizione/aggiornamento":
                continue
            try:
                name = namesubst[name]
            except:
                pass
            try:
                d = CET.localize(datetime.datetime.strptime(ncovdatapoint[0].strip(),"%Y-%m-%d %H:%M:%S"))
            except:
                d = CET.localize(datetime.datetime.strptime(ncovdatapoint[0].strip(),"%Y-%m-%dT%H:%M:%S"))
            numcaseslookup[name] = buildhelpers.datapoint(
                numcases= int(ncovdatapoint[9]) if ncovdatapoint[9] != "" else 0,
                timestamp= d,
                sourceurl= "https://github.com/pcm-dpc/COVID-19/blob/master/dati-province/dpc-covid19-ita-province.csv"
            )
            
    return numcaseslookup

numcaseslookup = readNewCSV()        
    
buildhelpers.processGEOJSON("ITALY", "./limits_IT_provinces_simplified.geojson", "prov_name", "prov_istat_code", numcaseslookup, italypop)
       
