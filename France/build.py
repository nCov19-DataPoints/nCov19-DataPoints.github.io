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

CET = pytz.timezone('CET')

regionpop = {
	"Île-de-France":12117132,
	"Auvergne-Rhône-Alpes":7916889,
	"Hauts-de-France":6006870,
	"Nouvelle-Aquitaine":5935603,
	"Occitanie":5808435,
	"Grand Est":5555186,
	"Provence-Alpes-Côte d'Azur":5021928,
	"Pays de la Loire":3737632,
	"Normandie":3335929,
	"Bretagne":3306529,
	"Bourgogne-Franche-Comté":2818338,
	"Centre-Val de Loire":2577866,
	"La Réunion":852924,
	"Guadeloupe":394110,
	"Martinique":376480,
	"Corse":330455,
	"Guyane":269352,
	"Mayotte":256518
};

departementpop = {
	"Nord":2595536,
	"Paris":2229621,
	"Bouches-du-Rhône":1993177,
	"Rhône":1779845,
	"Hauts-de-Seine":1591403,
	"Seine-Saint-Denis":1552482,
	"Gironde":1505517,
	"Pas-de-Calais":1465205,
	"Yvelines":1418484,
	"Seine-et-Marne":1365200,
	"Val-de-Marne":1354005,
	"Loire-Atlantique":1328620,
	"Haute-Garonne":1298562,
	"Seine-Maritime":1254609,
	"Essonne":1253931,
	"Isère":1235387,
	"Val-d'Oise":1194681,
	"Bas-Rhin":1109460,
	"Hérault":1092331,
	"Alpes-Maritimes":1080771,
	"Moselle":1046873,
	"Var":1028583,
	"Ille-et-Vilaine":1019923,
	"Finistère":903921,
	"Réunion":835103,
	"Oise":815400,
	"Maine-et-Loire":800191,
	"Haute-Savoie":769677,
	"Haut-Rhin":758723,
	"Loire":756715,
	"Morbihan":737778,
	"Gard":733201,
	"Meurthe-et-Moselle":731004,
	"Calvados":689945,
	"Loiret":665587,
	"Pyrénées-Atlantiques":664057,
	"Vendée":655506,
	"Puy-de-Dôme":640999,
	"Charente-Maritime":633417,
	"Ain":619497,
	"Indre-et-Loire":600252,
	"Côtes-d'Armor":597085,
	"Eure":595043,
	"Somme":571675,
	"Marne":569999,
	"Sarthe":569035,
	"Saône-et-Loire":556222,
	"Vaucluse":549949,
	"Aisne":540067,
	"Doubs":533320,
	"Côte-d'Or":529761,
	"Manche":499919,
	"Drôme":494712,
	"Pyrénées-Orientales":462705,
	"Eure-et-Loir":432967,
	"Vienne":431248,
	"Savoie":423715,
	"Dordogne":416909,
	"Guadeloupe":402119,
	"Landes":397226,
	"Martinique":385551,
	"Tarn":381927,
	"Haute-Vienne":375856,
	"Vosges":375226,
	"Deux-Sèvres":371632,
	"Aude":364877,
	"Charente":353482,
	"Allier":343431,
	"Yonne":341483,
	"Lot-et-Garonne":333180,
	"Loir-et-Cher":332001,
	"Ardèche":320379,
	"Cher":311650,
	"Mayenne":307500,
	"Aube":306581,
	"Orne":288848,
	"Ardennes":280907,
	"Aveyron":277740,
	"Jura":260502,
	"Tarn-et-Garonne":250342,
	"Guyane":244118,
	"Corrèze":240781,
	"Haute-Saône":238956,
	"Hautes-Pyrénées":228868,
	"Indre":228091,
	"Haute-Loire":226203,
	"Nièvre":215221,
	"Mayotte":212645,
	"Meuse":192094,
	"Gers":190276,
	"Haute-Marne":181521,
	"Lot":173758,
	"Haute-Corse":170974,
	"Alpes-de-Haute-Provence":161916,
	"Ariège":152684,
	"Corse-du-Sud":149234,
	"Cantal":147035,
	"Territoire de Belfort":144318,
	"Hautes-Alpes":139279,
	"Creuse":120872,
	"Lozère":76607,
	"La Réunion":852924,
};

#regiongeojson = "./regions-version-simplifiee.geojson"
regiongeojson = "./regions-avec-outre-mer_simplified.geojson"
#departementgeojson = "./departements-version-simplifiee.geojson"
departementgeojson = "./departements-avec-outre-mer_simplified.geojson"

def readNewCSV():
    numcaseslookup = dict()
    
    namesubst = {
        "Ile-de-France": "Île-de-France",
        "Provence-Alpes-Côte d’Azur": "Provence-Alpes-Côte d'Azur",
        "Haute-Pyrénées": "Hautes-Pyrénées",
        "Vendee": "Vendée",
        "Territoire-de-Belfort": "Territoire de Belfort",
        "Essone": "Essonne",
        "Saint-Saint-Denis": "Seine-Saint-Denis",
        "Corse du Sud": "Corse-du-Sud"
        }
    url="https://github.com/opencovid19-fr/data/raw/master/dist/chiffres-cles.csv"
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('utf-8')

    with StringIO(text) as f:
        # Gather departements and regions, for now use departements even though the data is not quite as current
        numcasesregion = dict()
        numcasesdepartement = dict()
        csvreader = csv.reader(f, delimiter=',')
        for ncovdatapoint in csvreader:
            if ncovdatapoint[1] != "region" and ncovdatapoint[1] != "departement":
                continue
            d = CET.localize(datetime.datetime.strptime(ncovdatapoint[0], "%Y-%m-%d"))
            name = ncovdatapoint[3].strip();
            if name=="Côtes d'Armor": # duplicate? There is also Côtes-d'Armor with the same ID
                continue
            try:
                name = namesubst[name]
            except:
                pass
            v = buildhelpers.datapoint(
                numcases = int(ncovdatapoint[4]) if ncovdatapoint[4] != "" else 0,
                timestamp = d,
                sourceurl = ncovdatapoint[7]
                )
            if ncovdatapoint[1] == "departement":           
                if not (name in numcasesdepartement) or d>numcasesdepartement[name].timestamp:
                    numcasesdepartement[name] = v
            else:
                if not (name in numcasesregion) or d>numcasesregion[name].timestamp:
                    numcasesregion[name] = v
        if len(numcasesdepartement)>0:
            numcaseslookup = numcasesdepartement
            francepop = departementpop
            francegeojson = departementgeojson
        else:
            numcaseslookup = numcasesregion
            francepop = regionpop
            francegeojson = regiongeojson

    return numcaseslookup, francegeojson, francepop

numcaseslookup, francegeojson, francepop = readNewCSV()

buildhelpers.processGEOJSON("FRANCE", francegeojson,"nom", "code", numcaseslookup, francepop)

       
