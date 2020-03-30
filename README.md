# nCov19-DataPoints
Corona Virus Data Points - gather data and facts and make them visible.

## Purpose
I found that most maps visualizing the Corona Virus data while very interesting did not help me judging the situation in local places - the resolution was too rough, and the numbers were in no relation to the population in the affected area. 

So I set [this map](https://ncov19-datapoints.github.io/) up with this repository.

## Feedback and help
If you think something is wrong or missing from the map, please add it to the [github issue tracker](https://github.com/nCov19-DataPoints/nCov19-DataPoints.github.io/issues). There is still plenty of stuff to do.

If you would like your country or region to be added, you can help by finding the required sources of data - preferably csv files by an official source, but other people gathering and cleaning up data with clear source attribution are also welcome. Or, if you feel like it, take the existing Python scripts for countries as an example and create your own one and send me a pull request. All help is welcome!

I will add more detailed help soon, until then, just ask.

## Repository structure
The structure of the repository is currently very simple:

* [index.html](./index.hmtl): the starting page if you go to http://ncov19-datapoints.github.io/, displaying the map with all the geojson files generating by the Python scripts for each country.
* For each country representing a separate data set with separate data sources there is a folder containing the following files (as an example the links go to the UK files):
  * [build.py](./UK/build.py): the script run each day at 20:00 UTC to update the ncov19map.js file.
    * There is a helper functions "generateOutput" in [buildhelpers.py](./buildhelpers.py). Use that to save your files to make sure the map can use them even if there are any style changes etc. I will add a few checks in there later to make sure the data can be used by the map.
  * [ncov19map.js](./UK/ncov19map.js): the file used by the map in "/Cov19.html"
  * [ncov19.geojson](./UK/ncov19.geojson) contains the same data as the ncov19map.js file, just without the minor JavaScript additions which make the data digestible to the Cov19.html file.
  * [ncov19.csv](./UK/ncov19.csv) contains the raw nCov19 data, this is useful for debugging. Or maybe somebody else wants to do something with that data.

## Thanks
Many thanks must go to the people gathering all the information which makes projects like this possible:

* Of course the [JHU repository](https://github.com/CSSEGISandData/2019-nCoV) is awesome.
* For France the [OpenCOVID19 France](https://github.com/opencovid19-fr) repository is a very good data source! They also have a very nice [dashboard](https://veille-coronavirus.fr/) for their data. I just wish the departements would not lag the regions, but that is complaining on a very high level.
* For Germany, Spain, Italy and England there are official data sources in a digestible format - a hurray to the civil servants doing that:
  * Italy: http://github.com/pcm-dpc/COVID-19
  * England: http://www.arcgis.com/home/item.html?id=e5fd11150d274bebaaf8fe2a7a2bda11 - though it would be nice if England would do the data more fine-grained - areas with a population of more than 1 million tend to obscure hotspots in the map.
  * Spain: https://covid19.isciii.es/ - also kind of large areas, obscuring hotspots.
  * Germany: https://npgeo-corona-npgeo-de.hub.arcgis.com/datasets/917fc37a709542548cc3be077a786c17_0/data (or http://corona.rki.de)
* The Swiss data can be found here: https://github.com/openZH/covid_19 (again thanks!).
  * If you need the data, feel free to use [the csv-file](./Germany/ncov19.csv). I aim to update it once a day, usually in the evening, to the best of my abilites. Once the RKI publishes the information, I will use that as a source, and the CSV file will then just contain the RKI data.
* For the US, the NY Times has graciously decided to make their data available to the public:
  * US: https://github.com/nytimes/covid-19-data
* Many thanks to all the people who refined the geojson data and made it ready-to-use:
  * Germany: http://opendatalab.de/projects/geojson-utilities/
  * Italy: http://github.com/openpolis/geojson-italy
  * France: http://github.com/gregoiredavid/france-geojson
  * UK: http://github.com/martinjc/UK-GeoJSON
  * Spain: https://covid19.isciii.es/
  * US: https://github.com/nytimes/covid-19-data
  * And http://github.com/mbloch/mapshaper is a very cool tool, if the too detailed geojson brings the browser to a crawl.
* Many thanks to http://openstreetmap.org - without them, no map!
* And also to the [Leaflet](http://leafletjs.com/) project, making it really easy to display geojson files!
* Also of course many thanks to github - this is an awesome platform with lots of free stuff!
