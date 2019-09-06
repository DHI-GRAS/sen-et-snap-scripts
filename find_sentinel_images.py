#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 27 11:30:29 2017

@author: root
"""

from collections import OrderedDict
from datetime import datetime
import glob
import os
import re
import zipfile

from sentinelsat.sentinel import SentinelAPI, SentinelAPIError, read_geojson, geojson_to_wkt


def find_sentinel_images(area_of_interest, date_start, date_end, platform_name, user, password,
                         datastore_base_path, download_path,
                         hub_address="https://scihub.copernicus.eu/apihub",
                         area_relation="Intersects", limit_to_tiles=[], other_search_keywords={},
                         limit_to_scenes=[], download=True, silent=False):

    def sprint(string):
        if not silent:
            print(string)
    
    ###################################
    identifiers = []
    products = {}
    product_paths = []

    sprint("Searching for scenes on "+hub_address)
    sprint(date_start+" - "+date_end)
    # search by polygon, time, and Hub query keywords
    file_name = []
    if limit_to_tiles:
        file_name = ["*_" + limit_to_tiles[i] + "_*" for i in range(len(limit_to_tiles))]
    file_name = file_name + limit_to_scenes
    if len(file_name) == 0:
       file_name = "*" 
    elif len(file_name) == 1:
        file_name = file_name[0]
    else:
        file_name = " OR ".join(file_name)
        file_name = "(" + file_name + ")"
        
    footprint = geojson_to_wkt(read_geojson(area_of_interest))
    products = _search_on_hub(user, password, hub_address, area=footprint,
                              area_relation=area_relation, date=(date_start, date_end),
                              platformname=platform_name, filename=file_name,
                              **other_search_keywords)
    products = _remove_duplicate_acquisitions(products)
    sprint("Found %i scenes" % len(products.keys()))
    for k in products.keys():
        identifiers.append(products[k]["identifier"])
        sprint(products[k]["identifier"])
    if not download:
        return list(products.values())

    ##################################
    # Then locate them in the IPT eodata store
    sprint("Locating scenes in eodata store...")
    for i, identifier in enumerate(identifiers):

        path = _search_on_datastore(datastore_base_path, identifier)
        # If they are not in the IPT eodata store (some S3 images are missing)
        # then download them and store in the download directory in case they
        # haven't been downloaded yet.
        if not path:
            if products:
                product = products[list(products.keys())[i]]
            else:
                product = _search_on_hub(user, password, hub_address, filename=identifier)
                if not product:
                    print("Product " + identifier + " does not exist and will not be downloaded!")
                    continue

            sprint("Scene not found in eodata store, downloading from "+hub_address+"...")
            path = _download_from_hub(product, download_path, user, password, hub_address, False)
            if not path:
                sprint("Could not download...")
                continue

        sprint(path)
        product_paths.append(path)

    return product_paths


def _search_on_hub(user, password, hub_address, **search_keywords):

    # Connect to the hub and search
    try:
        print(SentinelAPI.format_query(**search_keywords))
        hub = SentinelAPI(user, password, hub_address)
        products = hub.query(**search_keywords)
    except SentinelAPIError as e:
        print(e)
        print(SentinelAPI.format_query(**search_keywords))
        products = {}
    return products


def _search_on_datastore(datastore_base_path, product_identifier):
    m = re.findall("_(\d{4})(\d{2})(\d{2})T(\d{6})_", product_identifier)[-1]
    path = os.path.join(datastore_base_path, m[0], m[1], m[2], product_identifier+".*")

    if glob.glob(path):
        return path
    else:
        return None


def _download_from_hub(product, download_path, user, password,
                       hub_address="https://scihub.copernicus.eu/apihub", overwrite=False):

    path = os.path.join(download_path, product["identifier"] + ".*")
    if glob.glob(path) and not overwrite:
        return glob.glob(path)[0]
    else:
        # Connect to the hub and download
        try:
            hub = SentinelAPI(user, password, hub_address)
            p = hub.download(product["uuid"], download_path)
        except SentinelAPIError as e:
            print(e)
            return ""
        with zipfile.ZipFile(p["path"], "r") as z:
            z.extractall(download_path)
        os.remove(p["path"])
        return glob.glob(path)[0]


# Sometimes multiple copies of the same product (acquisition image) are returned from sci-hub due
# to different processing dates. In that case keep only the product with the latest processing
# date.
def _remove_duplicate_acquisitions(products):
    ingestion_dates = []
    acquisitions = []
    for product in products.values():
        if product["platformname"] == "Sentinel-2":
            match = re.match("(.*)(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})$", product["title"])
            acquisitions.append(match.group(1))
        else:
            match = re.match("(.*\d{8}T\d{6}_\d{8}T\d{6}_)\d{8}T\d{6}(.*)", product["title"])
            acquisitions.append(match.group(1)+match.group(2))
        ingestion_dates.append(product["ingestiondate"])
    unique_acquisitions = set(acquisitions)
    keep_products = OrderedDict()
    for acquisition in unique_acquisitions:
        scene_index = [i for i, e in enumerate(acquisitions) if e == acquisition]
        keep = None
        latest_date = datetime(1, 1, 1)
        for i in scene_index:
            if ingestion_dates[i] > latest_date:
                keep = i
                latest_date = ingestion_dates[i]
        keep_products[list(products.keys())[keep]] = list(products.values())[keep]
    return keep_products
