# -*- coding: utf-8 -*-
"""
Created on Tue Jul 17 14:47:50 2018

@author: rmgu
"""

import os
import datetime

import numpy as np
from osgeo import gdal, osr
import netCDF4
import cdsapi

from pyTSEB import meteo_utils as met
from pyDMS.pyDMSUtils import saveImg, openRaster, getRasterInfo

# Acceleration of gravity (m s-2)
GRAVITY = 9.80665
# Blending height of 100 m
Z_BH = 100.0


def download_CDS_data(date_start, date_end, variables, target, overwrite=False, area=None):

    s = {}

    s["variable"] = variables
    s["product_type"] = "reanalysis"
    s["date"] = date_start+"/"+date_end
    s["time"] = [str(t).zfill(2)+":00" for t in range(0, 24, 1)]
    if area:
        s["area"] = area
    s["format"] = "netcdf"

    # Connect to the server and download the data
    if not os.path.exists(target) or overwrite:
        c = cdsapi.Client()
        c.retrieve("reanalysis-era5-single-levels", s, target)
    print("Downloaded")


def get_ECMWF_data(ecmwf_data_file, field, timedate_UTC, elev, time_zone, rect_ecmwf, rect_elev):

    ncfile = netCDF4.Dataset(ecmwf_data_file, 'r')
    # Find the location of bracketing dates
    time = ncfile.variables['time']
    dates = netCDF4.num2date(time[:], time.units, time.calendar)
    beforeI, afterI, frac = _bracketing_dates(dates, timedate_UTC)
    if beforeI is None:
        ncfile.close()
        return None
    time = None
    ncfile.close()

    if field == "air_temperature":
        print("air_temperature")
        t2m, gt, proj = _getECMWFTempInterpData(ecmwf_data_file, "t2m", beforeI, afterI, frac,
                                                rect_ecmwf)
        # Get geopotential height at which Ta is calculated
        z, gt, proj = _getECMWFTempInterpData(ecmwf_data_file, "z", beforeI, afterI, frac,
                                              rect_ecmwf)
        z /= GRAVITY
        d2m, gt, proj = _getECMWFTempInterpData(ecmwf_data_file, "d2m", beforeI, afterI, frac,
                                                rect_ecmwf)
        ea = calc_vapour_pressure(d2m)
        sp, gt, proj = _getECMWFTempInterpData(ecmwf_data_file, "sp", beforeI, afterI, frac,
                                               rect_ecmwf)
        p = calc_pressure_mb(sp)
        # Calcultate temperature at 0m datum height
        T_datum = calc_air_temperature_blending_height(t2m, ea, p, 0, z_ta=z+2.0)
        # Resample dataset and calculate actual blendingh height temperature based on input
        # elevation data
        ea = _ECMWFRespampleData(ea, gt, proj, elev, rect_elev)
        p = _ECMWFRespampleData(p, gt, proj, elev, rect_elev)
        T_datum = _ECMWFRespampleData(T_datum, gt, proj, elev, rect_elev)
        elev_data = raster_data(elev, rect=rect_elev)
        data = calc_air_temperature_blending_height(T_datum, ea, p, elev_data+Z_BH, z_ta=0)

    elif field == "vapour_pressure":
        print("vp")
        d2m, gt, proj = _getECMWFTempInterpData(ecmwf_data_file, "d2m", beforeI, afterI, frac,
                                                rect_ecmwf)
        data = calc_vapour_pressure(d2m)
        data = _ECMWFRespampleData(data, gt, proj, elev, rect_elev)

    elif field == "wind_speed":
        print("ws")
        u100, gt, proj = _getECMWFTempInterpData(ecmwf_data_file, "u100", beforeI, afterI, frac,
                                                 rect_ecmwf)
        v100, gt, proj = _getECMWFTempInterpData(ecmwf_data_file, "v100", beforeI, afterI, frac,
                                                 rect_ecmwf)
        # Combine the two components of wind speed and calculate speed at blending height
        ws100 = calc_wind_speed(u100, v100)
        data = _ECMWFRespampleData(ws100, gt, proj, elev, rect_elev)

    elif field == "air_pressure":
        print("ap")
        sp, gt, proj = _getECMWFTempInterpData(ecmwf_data_file, "sp", beforeI, afterI, frac,
                                               rect_ecmwf)
        # Convert pressure from pascals to mb
        data = calc_pressure_mb(sp)
        data = _ECMWFRespampleData(data, gt, proj, elev, rect_elev)

    elif field == "clear_sky_solar_radiation":
        print("cssr")
        ssrdc, gt, proj = _getECMWFTempInterpData(ecmwf_data_file, "ssrdc", beforeI, afterI, frac,
                                                  rect_ecmwf)
        # Convert from Jules to Watts
        data = ssrdc / 3600.0
        data = _ECMWFRespampleData(data, gt, proj, elev, rect_elev)

    elif field == "average_daily_solar_irradiance":
        print("adsi")
        # Find midnight in local time and convert to UTC time
        date_local = (timedate_UTC + datetime.timedelta(hours=time_zone)).date()
        midnight_local = datetime.datetime.combine(date_local, datetime.time())
        midnight_UTC = midnight_local - datetime.timedelta(hours=time_zone)
        # Interpolate solar irradiance over 24 hour period starting at midnight local time
        data, gt, proj = _getECMWFIntegratedData(ecmwf_data_file, "ssrd", midnight_UTC, rect_ecmwf,
                                                 time_window=24)
        data = _ECMWFRespampleData(data, gt, proj, elev, rect_elev)
    else:
        raise RuntimeError("Unknown field: %s!" % field)

    return data


def calc_air_temperature_blending_height(ta, ea, p, z_bh, z_ta=2.0):
    lapse_rate = met.calc_lapse_rate_moist(ta, ea, p)
    ta_bh = ta - lapse_rate * (z_bh - z_ta)
    return ta_bh


def calc_vapour_pressure(td):
    # output in mb
    td = td - 273.15
    e = 6.11 * np.power(10, (7.5 * td)/(237.3 + td))
    return e


def calc_wind_speed(u, v):
    ws = (u**2 + v**2)**0.5
    ws = np.maximum(ws, 1.0)
    return ws


def calc_pressure_mb(sp):
    # Convert from pascals to mb
    sp_mb = sp/100.0
    return sp_mb


def calc_tcwv_cm(tcwv):
    # Conert from from kg/m**2 to g/cm**2
    return tcwv/10.0


def _getECMWFTempInterpData(ncfile, var_name, before_I, after_I, frac, rect):
    ds = gdal.Open('NETCDF:"'+ncfile+'":'+var_name)
    if ds is None:
        raise RuntimeError("Variable %s does not exist in file %s." % (var_name, ncfile))

    # Get some metadata
    scale = ds.GetRasterBand(before_I+1).GetScale()
    offset = ds.GetRasterBand(before_I+1).GetOffset()
    no_data_value = ds.GetRasterBand(before_I+1).GetNoDataValue()
    # Report geolocation of the top-left pixel of rectangle
    gt = list(ds.GetGeoTransform())
    gt[0] = gt[0] + gt[1]*rect.x
    gt[3] = gt[3] + gt[5]*rect.y
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(4326)
    proj = sr.ExportToWkt()

    # Read the right time layers
    try:
        data_before = ds.GetRasterBand(before_I+1).ReadAsArray(rect.x, rect.y, rect.width,
                                                                  rect.height)
        data_before = (data_before.astype(float) * scale) + offset
        data_before[data_before == no_data_value] = np.nan
        data_after = ds.GetRasterBand(after_I+1).ReadAsArray(rect.x, rect.y, rect.width,
                                                             rect.height)
        data_after = (data_after.astype(float) * scale) + offset
        data_after[data_after == no_data_value] = np.nan
    except AttributeError:
        ds = None
        raise RuntimeError("ECMWF file does not contain data for the requested date.")

    # Perform temporal interpolation
    data = data_before*frac + data_after*(1.0-frac)

    return data, gt, proj


def _ECMWFRespampleData(data, gt, proj, template_file, rect_template):
    # Subset and reproject to the template file extent and projection
    ds_out = save_image(data, gt, proj, "MEM")
    ds_out_proj = resample_with_gdalwarp(ds_out, template_file, rect_template)
    data = ds_out_proj.GetRasterBand(1).ReadAsArray()
    ds_out_proj = None

    return data


def _getECMWFIntegratedData(ncfile, var_name, date_time, rect, time_window=24,):

    # Open the netcdf time dataset
    fid = netCDF4.Dataset(ncfile, 'r')
    time = fid.variables['time']
    dates = netCDF4.num2date(time[:], time.units, time.calendar)
    del fid

    # Get the time right before date_time, to use it as integrated baseline
    date_0, _, _ = _bracketing_dates(dates, date_time)
    # Get the time right before the temporal witndow set
    date_1, _, _ = _bracketing_dates(dates, date_time + datetime.timedelta(hours=time_window))

    ds = gdal.Open('NETCDF:"'+ncfile+'":'+var_name)
    if ds is None:
        raise RuntimeError("Variable %s does not exist in file %s." % (var_name, ncfile))
    # Get some metadata
    scale = ds.GetRasterBand(date_0+1).GetScale()
    offset = ds.GetRasterBand(date_0+1).GetOffset()
    no_data_value = ds.GetRasterBand(date_0+1).GetNoDataValue()
    # Report geolocation of the top-left pixel of rectangle
    gt = list(ds.GetGeoTransform())
    gt[0] = gt[0] + gt[1]*rect.x
    gt[3] = gt[3] + gt[5]*rect.y
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(4326)
    proj = sr.ExportToWkt()

    # Forecasts of ERA5 the accumulations are since the previous post processing
    # (archiving)
    data_ref = 0

    # Initialize output variable
    cummulated_value = 0.

    try:
        for date_i in range(date_0+1, date_1+1):
            # Read the right time layers
            data = ds.GetRasterBand(date_i+1).ReadAsArray(rect.x, rect.y, rect.width, rect.height)
            data = (data.astype(float) * scale) + offset
            data[data == no_data_value] = 0
            # The time step value is the difference between  the actual timestep value and the
            # previous value
            cummulated_value += (data - data_ref)
    except AttributeError:
        ds = None
        raise RuntimeError("ECMWF file does not contain data for the requested date")

    # Convert to average W m^-2
    cummulated_value = cummulated_value / (time_window * 3600.)

    return cummulated_value, gt, proj


def _bracketing_dates(date_list, target_date):
    date_list = list(date_list)
    try:
        before = max([x for x in date_list if (target_date - x).total_seconds() >= 0])
        after = min([x for x in date_list if (target_date - x).total_seconds() <= 0])
    except ValueError:
        return None, None, np.nan
    if before == after:
        frac = 1
    else:
        frac = float((after - target_date).total_seconds())/float((after-before).total_seconds())
    return date_list.index(before), date_list.index(after), frac


def save_image(data, geotransform, projection, filename):
    return saveImg(data, geotransform, projection, filename)


def resample_with_gdalwarp(src, template, rect_template):
    # Get template projection, extent and resolution
    proj, gt, sizeX, sizeY, _, _ = getRasterInfo(template)
    extent = [gt[0]+gt[1]*rect_template.x, gt[3]+gt[5]*(rect_template.y + rect_template.height),
              gt[0]+gt[1]*(rect_template.x + rect_template.width), gt[3]+gt[5]*rect_template.y]

    # Resample with GDAL warp
    out_ds = gdal.Warp("",
                       src,
                       format="MEM",
                       dstSRS=proj,
                       xRes=gt[1],
                       yRes=gt[5],
                       outputBounds=extent,
                       resampleAlg="cubicspline")
    return out_ds


def raster_data(raster, bands=1, rect=None):

    def _read_band(fid, band, rect):
        if rect:
            return fid.GetRasterBand(band).ReadAsArray(rect.x, rect.y, rect.width, rect.height)
        else:
            return fid.GetRasterBand(band).ReadAsArray()

    fid, closeOnExit = openRaster(raster)
    if type(bands) == int:
        bands = [bands]

    data = None
    for band in bands:
        if data is None:
            data = _read_band(fid, band, rect)
        else:
            data = np.dstack((data, _read_band(fid, band, rect)))

    if closeOnExit:
        fid = None

    return data
