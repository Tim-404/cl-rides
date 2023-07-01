"""Stores locations and corresponding distances in a matrix.
Distance values acquired from Google Maps Matrix API.
"""

import requests, json
import googlemaps
import pandas as pd
import lib.postprocessing as post
import lib.preprocessing as prep
from lib.rides_data import *

# TODO: protect api_key, env?
api_key = 'AIzaSyBzBfzvl1Xc9SngKPqF0BMHRktapxVhzhI'
gmaps = googlemaps.Client(key=api_key)

# This (county) specifier works well for all locations extant in our specific Google Sheets so far
LOCATION_SPECIFIER = ", San Diego" 

# Nested hashmap representing the map
map_dictionary = {'Sources': {}, 'Destinations': {}}
map_json = ''

############# EXAMPLE DIST MTX API JSON RETURN VAL ####################
"""
{
  "destination_addresses":
    ["San Francisco, Californie, États-Unis", "Victoria, BC, Canada"],
  "origin_addresses":
    ["Vancouver, BC, Canada", "Seattle, Washington, États-Unis"],
  "rows":
    [
      {
        "elements":
          [
            {
              "distance": { "text": "1 712 km", "value": 1711765 },
              "duration": { "text": "3 jours 16 heures", "value": 318119 },
              "status": "OK",
            },
            {
              "distance": { "text": "140 km", "value": 139695 },
              "duration": { "text": "6 heures 49 minutes", "value": 24567 },
              "status": "OK",
            },
          ],
      },
      {
        "elements":
          [
            {
              "distance": { "text": "1 452 km", "value": 1451704 },
              "duration": { "text": "3 jours 2 heures", "value": 266680 },
              "status": "OK",
            },
            {
              "distance": { "text": "146 km", "value": 146500 },
              "duration": { "text": "2 heures 53 minutes", "value": 10374 },
              "status": "OK",
            },
          ],
      },
    ],
  "status": "OK",
}
"""

# Map data
locations = set() # TODO: persist locations acquired from Google Distance Matrix API
geocodes = [] # may contain duplicates
map_data = {} 
incomplete_locations = set()

# FIXME: response.text.status: "MAX_ELEMENTS_EXCEEDED". At most 100 elements can be computed in one request
def update_map(drivers_df: pd.DataFrame, riders_df: pd.DataFrame, debug: bool):
    """Incorporate names of new locations
    """
    # Form set of all locations
    hasNewLocation = False
    for index in riders_df.index:
        prevLen = len(locations)
        locations.add(riders_df.loc[index].at[RIDER_LOCATION_KEY])
        
        if len(locations) != prevLen:
            hasNewLocation = True
            
    print("locations")
    print(locations)

    # TODO: replace naive location check. Use actual geocoded information to ignore trivial differences in location strings
    if hasNewLocation:
        print("encoding map")
        _encode_map()

def _encode_map():
    """Updates map graph representation based on names of new locations
    """
    # TODO: use persisted locations array to detect if new locations exist, otherwise do not query
    
    # Construct distance matrix data HTTP request
    url = "https://maps.googleapis.com/maps/api/distancematrix/json?destinations="
    
    # Add destinations to request
    addedLocCtr = 0
    url_destinations = ""
    
    for location_str in locations:

      print("####### location_str ###############################")
      print(location_str)
      
      location_str += LOCATION_SPECIFIER

      # Obtain place_ids based on Google Forms input string geocode
      geocode_result = gmaps.geocode(location_str)

      print("geocode_result")
      print(geocode_result)

      if (geocode_result == []):
          # TODO: handle invalid query
          print("NO GEOCODE RESULT FOR " + location_str)
          incomplete_locations.add(location_str)
          continue

      # Add destination by place_id
      url_destinations += "place_id:"

      geocodes.append(geocode_result)
      formatted_address = geocode_result[0]['formatted_address']
      location = geocode_result[0]['geometry']['location']
      lat = location['lat']
      lng = location['lng']
      place_id = geocode_result[0]['place_id']

      url_destinations += place_id

      print("formatted_address of added location:")
      print(formatted_address)

      addedLocCtr += 1
      if addedLocCtr < len(locations):
          url_destinations += "|"

    url += url_destinations
      
    # Add origins to request, identical to destinations to obtain a cartesian product of paths
    url += "&origins="
    url_origins = url_destinations
    url += url_origins

    url += "&units=imperial"
    url = url + "&key=" + api_key

    print("url")
    print(url)

    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)

    print("response.text")
    print(response.text)

    print("incomplete_locations")
    print(incomplete_locations)

    _store_map(response.text)

def _store_map(map_json):
    with open("map.json",'w') as file_object:
        json.dump(map_json, file_object)


# def _load_map():
#     with open("map.json",'r') as file_object:
#         map_json = json.load(map.json)