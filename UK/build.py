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

englandpop = {
    "County Durham":526980,
    "Darlington":106566,
    "Hartlepool":93242,
    "Middlesbrough":140545,
    "Northumberland":320274,
    "Redcar and Cleveland":136718,
    "Stockton-on-Tees":197213,
    "Gateshead":202508,
    "Newcastle upon Tyne":300196,
    "North Tyneside":205985,
    "South Tyneside":150265,
    "Sunderland":277417,
    "Blackburn with Darwen":148942,
    "Blackpool":139305,
    "Cheshire East":380790,
    "Cheshire West and Chester":340502,
    "Halton":128432,
    "Warrington":209547,
    "Cumbria":498888,
    "Allerdale":97527,
    "Barrow-in-Furness":67137,
    "Carlisle":108387,
    "Copeland":68424,
    "Eden":52881,
    "South Lakeland":104532,
    "Bolton":285372,
    "Bury":190108,
    "Manchester":547627,
    "Oldham":235623,
    "Rochdale":220001,
    "Salford":254408,
    "Stockport":291775,
    "Tameside":225197,
    "Trafford":236370,
    "Wigan":326088,
    "Lancashire":1210053,
    "Burnley":88527,
    "Chorley":116821,
    "Fylde":79770,
    "Hyndburn":80815,
    "Lancaster":144246,
    "Pendle":91405,
    "Preston":141818,
    "Ribble Valley":60057,
    "Rossendale":70895,
    "South Ribble":110527,
    "West Lancashire":113949,
    "Wyre":111223,
    "Knowsley":149571,
    "Liverpool":494814,
    "Sefton":275396,
    "St. Helens":180049,
    "Wirral":323235,
    "East Riding of Yorkshire":339614,
    "Kingston upon Hull, City of":260645,
    "North East Lincolnshire":159821,
    "North Lincolnshire":172005,
    "York":209893,
    "North Yorkshire":614505,
    "Craven":56832,
    "Hambleton":91134,
    "Harrogate":160533,
    "Richmondshire":53244,
    "Ryedale":54920,
    "Scarborough":108736,
    "Selby":89106,
    "Barnsley":245199,
    "Doncaster":310542,
    "Rotherham":264671,
    "Sheffield":582506,
    "Bradford":537173,
    "Calderdale":210082,
    "Kirklees":438727,
    "Leeds":789194,
    "Wakefield":345038,
    "Derby":257174,
    "Leicester":355218,
    "Nottingham":331069,
    "Rutland":39697,
    "Derbyshire":796142,
    "Amber Valley":126678,
    "Bolsover":79530,
    "Chesterfield":104628,
    "Derbyshire Dales":71977,
    "Erewash":115490,
    "High Peak":92221,
    "North East Derbyshire":101125,
    "South Derbyshire":104493,
    "Leicestershire":698268,
    "Blaby":100421,
    "Charnwood":182643,
    "Harborough":92499,
    "Hinckley and Bosworth":112423,
    "Melton":51100,
    "North West Leicestershire":102126,
    "Oadby and Wigston":57056,
    "Lincolnshire":755833,
    "Boston":69366,
    "East Lindsey":140741,
    "Lincoln":99039,
    "North Kesteven":115985,
    "South Holland":93980,
    "South Kesteven":141853,
    "West Lindsey":94869,
    "Northamptonshire":747622,
    "Corby":70827,
    "Daventry":84484,
    "East Northamptonshire":93906,
    "Kettering":101266,
    "Northampton":225146,
    "South Northamptonshire":92515,
    "Wellingborough":79478,
    "Nottinghamshire":823126,
    "Ashfield":127151,
    "Bassetlaw":116839,
    "Broxtowe":113272,
    "Gedling":117786,
    "Mansfield":108841,
    "Newark and Sherwood":121566,
    "Rushcliffe":117671,
    "Herefordshire, County of":192107,
    "Shropshire":320274,
    "Stoke-on-Trent":255833,
    "Telford and Wrekin":177799,
    "Staffordshire":875219,
    "Cannock Chase":100109,
    "East Staffordshire":118574,
    "Lichfield":103965,
    "Newcastle-under-Lyme":129490,
    "South Staffordshire":112126,
    "Stafford":135880,
    "Staffordshire Moorlands":98397,
    "Tamworth":76678,
    "Warwickshire":571010,
    "North Warwickshire":64850,
    "Nuneaton and Bedworth":128902,
    "Rugby":107194,
    "Stratford-on-Avon":127580,
    "Warwick":142484,
    "Birmingham":1141374,
    "Coventry":366785,
    "Dudley":320626,
    "Sandwell":327378,
    "Solihull":214909,
    "Walsall":283378,
    "Wolverhampton":262008,
    "Worcestershire":592057,
    "Bromsgrove":98662,
    "Malvern Hills":78113,
    "Redditch":84989,
    "Worcester":101891,
    "Wychavon":127340,
    "Wyre Forest":101062,
    "Bedford":171623,
    "Central Bedfordshire":283606,
    "Luton":214109,
    "Peterborough":201041,
    "Southend-on-Sea":182463,
    "Thurrock":172525,
    "Cambridgeshire":651482,
    "Cambridge":125758,
    "East Cambridgeshire":89362,
    "Fenland":101491,
    "Huntingdonshire":177352,
    "South Cambridgeshire":157519,
    "Essex":1477764,
    "Basildon":185862,
    "Braintree":151561,
    "Brentwood":76550,
    "Castle Point":90070,
    "Chelmsford":177079,
    "Colchester":192523,
    "Epping Forest":131137,
    "Harlow":86594,
    "Maldon":64425,
    "Rochford":86981,
    "Tendring":145803,
    "Uttlesford":89179,
    "Hertfordshire":1184365,
    "Broxbourne":96876,
    "Dacorum":154280,
    "East Hertfordshire":148105,
    "Hertsmere":104205,
    "North Hertfordshire":133214,
    "St Albans":147373,
    "Stevenage":87754,
    "Three Rivers":93045,
    "Watford":96767,
    "Welwyn Hatfield":122746,
    "Norfolk":903680,
    "Breckland":139329,
    "Broadland":129464,
    "Great Yarmouth":99370,
    "King's Lynn and West Norfolk":151811,
    "North Norfolk":104552,
    "Norwich":141137,
    "South Norfolk":138017,
    "Suffolk":758556,
    "Babergh":91401,
    "East Suffolk":248249,
    "Ipswich":137532,
    "Mid Suffolk":102493,
    "West Suffolk":178881,
    "Camden":262226,
    "City of London":8706,
    "Hackney":279665,
    "Hammersmith and Fulham":185426,
    "Haringey":270624,
    "Islington":239142,
    "Kensington and Chelsea":156197,
    "Lambeth":325917,
    "Lewisham":303536,
    "Newham":352005,
    "Southwark":317256,
    "Tower Hamlets":317705,
    "Wandsworth":326474,
    "Westminster":255324,
    "Barking and Dagenham":211998,
    "Barnet":392140,
    "Bexley":247258,
    "Brent":330795,
    "Bromley":331096,
    "Croydon":385346,
    "Ealing":341982,
    "Enfield":333869,
    "Greenwich":286186,
    "Harrow":250149,
    "Havering":257810,
    "Hillingdon":304824,
    "Hounslow":270782,
    "Kingston upon Thames":175470,
    "Merton":206186,
    "Redbridge":303858,
    "Richmond upon Thames":196904,
    "Sutton":204525,
    "Waltham Forest":276700,
    "Bracknell Forest":121676,
    "Brighton and Hove":290395,
    "Isle of Wight":141538,
    "Medway":277855,
    "Milton Keynes":268607,
    "Portsmouth":215133,
    "Reading":163203,
    "Slough":149112,
    "Southampton":252796,
    "West Berkshire":158527,
    "Windsor and Maidenhead":150906,
    "Wokingham":167979,
    "Buckinghamshire":540059,
    "Aylesbury Vale":199448,
    "Chiltern":95927,
    "South Bucks":70043,
    "Wycombe":174641,
    "East Sussex":554590,
    "Eastbourne":103160,
    "Hastings":92855,
    "Lewes":102744,
    "Rother":95656,
    "Wealden":160175,
    "Hampshire":1376316,
    "Basingstoke and Deane":175729,
    "East Hampshire":120681,
    "Eastleigh":131819,
    "Fareham":116339,
    "Gosport":85283,
    "Hart":96293,
    "Havant":125813,
    "New Forest":179753,
    "Rushmoor":95142,
    "Test Valley":125169,
    "Winchester":124295,
    "Kent":1568623,
    "Ashford":129281,
    "Canterbury":164553,
    "Dartford":109709,
    "Dover":116969,
    "Folkestone and Hythe":112578,
    "Gravesham":106385,
    "Maidstone":169955,
    "Sevenoaks":120293,
    "Swale":148519,
    "Thanet":141819,
    "Tonbridge and Malling":130508,
    "Tunbridge Wells":118054,
    "Oxfordshire":687524,
    "Cherwell":149161,
    "Oxford":154327,
    "South Oxfordshire":140504,
    "Vale of White Horse":133732,
    "West Oxfordshire":109800,
    "Surrey":1189934,
    "Elmbridge":136626,
    "Epsom and Ewell":79928,
    "Guildford":147889,
    "Mole Valley":87253,
    "Reigate and Banstead":147757,
    "Runnymede":88000,
    "Spelthorne":99334,
    "Surrey Heath":88874,
    "Tandridge":87496,
    "Waverley":125610,
    "Woking":101167,
    "West Sussex":858852,
    "Adur":63869,
    "Arun":159827,
    "Chichester":120750,
    "Crawley":112448,
    "Horsham":142217,
    "Mid Sussex":149716,
    "Worthing":110025,
    "Bath and North East Somerset":192106,
    "Bournemouth, Christchurch and Poole":395784,
    "Bristol, City of":463405,
    "Cornwall":565968,
    "Dorset":376484,
    "Isles of Scilly":2242,
    "North Somerset":213919,
    "Plymouth":263100,
    "South Gloucestershire":282644,
    "Swindon":221996,
    "Torbay":135780,
    "Wiltshire":498064,
    "Devon":795286,
    "East Devon":144317,
    "Exeter":130428,
    "Mid Devon":81695,
    "North Devon":96110,
    "South Hams":86221,
    "Teignbridge":132844,
    "Torridge":68143,
    "West Devon":55528,
    "Gloucestershire":633558,
    "Cheltenham":117090,
    "Cotswold":89022,
    "Forest of Dean":86543,
    "Gloucester":129285,
    "Stroud":119019,
    "Tewkesbury":92599,
    "Somerset":559399,
    "Mendip":114881,
    "Sedgemoor":122791,
    "Somerset West and Taunton":153866,
    "South Somerset":167861,
    "Isle of Anglesey":69961,
    "Gwynedd":124178,
    "Conwy":117181,
    "Denbighshire":95330,
    "Flintshire":155593,
    "Wrexham":136126,
    "Powys":132447,
    "Ceredigion":72992,
    "Pembrokeshire":125055,
    "Carmarthenshire":187568,
    "Swansea":246466,
    "Neath Port Talbot":142906,
    "Bridgend":144876,
    "Vale of Glamorgan":132165,
    "Cardiff":364248,
    "Rhondda Cynon Taf":240131,
    "Merthyr Tydfil":60183,
    "Caerphilly":181019,
    "Blaenau Gwent":69713,
    "Torfaen":93049,
    "Monmouthshire":94142,
    "Newport":153302,
    "Antrim and Newtownabbey":142492,
    "Ards and North Down":160864,
    "Armagh City, Banbridge and Craigavon":214090,
    "Belfast":341877,
    "Causeway Coast and Glens":144246,
    "Derry City and Strabane":150679,
    "Fermanagh and Omagh":116835,
    "Lisburn and Castlereagh":144381,
    "Mid and East Antrim":138773,
    "Mid Ulster":147392,
    "Newry, Mourne and Down":180012,
    "Cornwall and Isles of Scilly":565968+2242,
    "Hackney and City of London":279665+8706
};

BST = pytz.timezone('GB')

def readNewCSV():
    namesubst = {
        "Hackney and City of London": "Hackney",
        "Cornwall and Isles of Scilly": "Cornwall",
        "Bournemouth": "Bournemouth, Christchurch and Poole",
        "Poole":  "Bournemouth, Christchurch and Poole"
        }
    url="https://github.com/tomwhite/covid-19-uk-data/raw/master/data/covid-19-cases-uk.csv"
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('utf-8')

    numcaseslookup = dict()
    with StringIO(text) as f:
        csvreader = csv.reader(f, delimiter=',')
        for ncovdatapoint in csvreader:
            name = ncovdatapoint[3].strip();
            if name == "Area" or name == "" or ncovdatapoint[1].strip()!="England" or name.lower()=="awaiting clarification" or name.lower()=="awaiting confirmation":
                continue
            try:
                name = namesubst[name]
            except:
                pass
            numstr = ncovdatapoint[4]
            try:
                num = int(ncovdatapoint[4].replace(",","")) if ncovdatapoint[4] != "" else 0
            except:
                if numstr=="1 to 4":
                    num = 2
                else:
                    raise
            try:
                d = BST.localize(datetime.datetime.strptime(ncovdatapoint[0].strip(), "%Y-%m-%d"))
            except:
                print("Failed to parse timestamp '" + ncovdatapoint[0].strip() + "'")
            if not name in numcaseslookup or numcaseslookup[name].timestamp<d:
                numcaseslookup[name] = datapoint(
                    numcases=num,
                    timestamp=d,
                    sourceurl="https://github.com/tomwhite/covid-19-uk-data"
                    )
            else:
                numcaseslookup[name].numcases += num
    return numcaseslookup

numcaseslookup = readNewCSV()

processGEOJSON("UK", "Counties_and_Unitary_Authorities_April_2019_Boundaries_EW_BUC.geojson", "ctyua19nm", "objectid", numcaseslookup, englandpop)

       
