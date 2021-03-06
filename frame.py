import subprocess
import fiona
import os
import os.path
import json
import shutil
import shapely
import geopandas as gpd
import numpy
import math
import geojson

import pdb

import pedestriansfirst


def from_id_hdc(hdc, folder_prefix = '', boundary_buffer = 0, kwargs = {}):
    #select city from ID number
    with fiona.open('GHS_STAT_UCDB2015MT_GLOBE_R2019A_V1_0.shp','r') as ucdb:
        for city in ucdb:
            if int(city['properties']['ID_HDC_G0']) == int(hdc):
                target = city
    return from_city(target, folder_prefix = folder_prefix, boundary_buffer = boundary_buffer, kwargs=kwargs)

def from_city(city, folder_prefix = '', boundary_buffer = 0, kwargs = {}):
    hdc = city['properties']['ID_HDC_G0']
    #save city geometry so that I can take an extract from planet.pbf within it
    if not os.path.isdir(str(hdc)):
        os.mkdir(str(hdc))
    if boundary_buffer > 0:
        boundaries = shapely.geometry.shape(city['geometry'])
        bound_latlon = gpd.GeoDataFrame(geometry = [boundaries])
        bound_latlon.crs = {'init':'epsg:4326'}
        longitude = round(numpy.mean(bound_latlon.geometry.centroid.x),10)
        utm_zone = int(math.floor((longitude + 180) / 6) + 1)
        utm_crs = '+proj=utm +zone={} +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(utm_zone)
        bound_utm = bound_latlon.to_crs(utm_crs)
        bound_utm.geometry = bound_utm.geometry.buffer(boundary_buffer*1000)
        bound_latlon = bound_utm.to_crs(epsg=4326)
        boundaries = bound_latlon.geometry.unary_union
        geom_in_geojson = geojson.Feature(geometry=boundaries, properties={})
        with open(str(hdc)+'/boundaries.geojson', 'w') as out:
            out.write(json.dumps(geom_in_geojson))
    else:
        with open(str(hdc)+'/boundaries.geojson', 'w') as out:
            out.write(json.dumps(city))
    #take extract from planet.pbf
    if not os.path.exists('{}/city.pbf'.format(str(hdc))):
        command = "osmium extract planet-latest.osm.pbf -p {}/boundaries.geojson -s complete_ways -v -o {}/city.pbf".format(str(hdc), str(hdc))
        print(command)
        subprocess.check_call(command.split(' '))
    command = "osmconvert {}/city.pbf -o={}/city.o5m".format(str(hdc),str(hdc))
    print(command)
    subprocess.check_call(command.split(' '))
    command = 'osmfilter {}/city.o5m --keep="highway=" -o={}/cityhighways.o5m'.format(str(hdc),str(hdc))
    print(command)
    subprocess.check_call(command, shell=True)
    command = ['osmfilter {}/cityhighways.o5m --drop="area=yes highway=link =motor =proposed =construction =abandoned =platform =raceway service=parking_aisle =driveway =private foot=no" -o={}/citywalk.o5m'.format(str(hdc),str(hdc))]
    print(command)
    subprocess.check_call(command, shell=True)
    
    folder = folder_prefix + str(hdc) + '/'
    
    return pedestriansfirst.pedestrians_first(city, folder_name = folder, **kwargs)

def get_pop(city):
    return city['properties']['P15']

#all cities in descending order
    #todo: read from all_results to skip cities i've already done
def all_cities():
    with fiona.open('GHS_STAT_UCDB2015MT_GLOBE_R2019A_V1_0.shp','r') as ucdb:
        cities = list(ucdb)
    cities.sort(key=get_pop, reverse = True)
    for city in cities:
        if os.path.exists('all_results.json'):
            with open('all_results.json','r') as in_file:
                all_results = json.load(in_file)
        else:
            all_results = {}
        if not str(city['properties']['ID_HDC_G0']) in all_results.keys():
            if not str(city['properties']['ID_HDC_G0']) == '4541': #there's one city in south sudan that doesn't work right.
                results = from_city(city)
                all_results.update({city['properties']['ID_HDC_G0']:results})
                with open('all_results.json','w') as out_file:
                    json.dump(all_results, out_file)

if __name__ == '__main__':
    all_cities()

#hdcs = { #test
#'Mexico City': 154,
#        }



#for city in hdcs.keys():
#    if not os.path.exists(str(hdcs[city])+'/results.json'):
#        from_id_hdc(hdcs[city])
#    else:
#        for file in ['city.o5m','cityhighways.o5m','citywalk.o5m']:
#            if os.path.exists(str(hdcs[city])+'/'+file):
#                os.remove(str(hdcs[city])+'/'+file)

