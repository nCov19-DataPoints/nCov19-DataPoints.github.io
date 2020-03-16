# nCov19-DataPoints
Corona Virus Data Points - gather data and facts and make them visible.

## Purpose
I found that most maps visualizing the Corona Virus data while very interesting did not help me judging the situation in local places - the resolution was too rough, and the numbers were in no relation to the population in the affected area. 

So I set [this map](https://ncov19-datapoints.github.io/NCov19.html) up with this repository.

## Feedback and help
If you think something is wrong or missing from the map, please add it to the [github issue tracker](https://github.com/nCov19-DataPoints/nCov19-DataPoints.github.io/issues). There is still plenty of stuff to do.

If you would like your country or region to be added, you can help by finding the required sources of data - preferably csv files by an official source, but other people gathering and cleaning up data with clear source attribution are also welcome. Or, if you feel like it, take the existing Python scripts for countries as an example and create your own one and send me a pull request. All help is welcome!

I will add more detailed help soon, until then, just ask.

## Repository structure
The structure of the repository is currently very simple:

* [index.html](./index.hmtl): the starting page if you go to http://ncov19-datapoints.github.io/, displaying the map with all the geojson files generating by the Python scripts for each country.
* For each country (separate data set with separate sources) a folder containing (links on the example of the UK):
  * [build.py](./UK/build.py): the script run each day at 20:00 UTC to update the ncov19map.js file.
    * There is a helper functions "generateOutput" in [buildhelpers.py](./buildhelpers.py). Use that to save your files to make sure the map can use them even if there are any style changes etc. I will add a few checks in there later to make sure the data can be used by the map.
  * [ncov19map.js](./UK/ncov19map.js): the file used by the map in "/Cov19.html"
  * [ncov19.geojson](./UK/ncov19.geojson) contains the same data as the ncov19map.js file, just without the minor JavaScript additions which make the data digestible to the Cov19.html file.
  * [ncov19.csv](./UK/ncov19.csv) contains the raw nCov19 data, this is useful for debugging. Or maybe somebody else wants to do something with that data.

