import click
import tempfile
import numpy as np
import os
import os.path as pth

from pyDMS.pyDMS import DecisionTreeSharpener

import gdal_utils as gu
import snappy_utils as su


@click.command()
@click.option('--sentinel_2_reflectance', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--sentinel_3_lst', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--high_res_dem', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--high_res_geom', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--lst_quality_mask', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--date_time_utc', required=True, type=click.DateTime(formats=['%Y-%m-%d %H:%M']))
@click.option('--elevation_band', required=True)
@click.option('--lst_good_quality_flags', required=True)
@click.option('--cv_homogeneity_threshold', required=True, type=click.FloatRange(0, 1))
@click.option('--moving_window_size', required=True, type=click.IntRange(1))
@click.option('--parallel_jobs', required=True, type=click.IntRange(1))
@click.option('--output', required=True, type=click.Path(dir_okay=False, exists=False))
def main(sentinel_2_reflectance, sentinel_3_lst, high_res_dem, high_res_geom, lst_quality_mask,
         date_time_utc, elevation_band, lst_good_quality_flags, cv_homogeneity_threshold,
         moving_window_size, parallel_jobs, output):

    # Derive illumination conditions from the DEM
    print('INFO: Deriving solar illumination conditions...')
    temp_file = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    temp_dem_file = temp_file.name
    temp_file.close()
    su.copy_bands_to_file(high_res_dem, temp_dem_file, [elevation_band])
    temp_slope_file = gu.slope_from_dem(temp_dem_file)
    temp_aspect_file = gu.aspect_from_dem(temp_dem_file)
    slope = gu.raster_data(temp_slope_file)
    aspect = gu.raster_data(temp_aspect_file)
    try:
        lat = su.read_snappy_product(high_res_geom, 'latitude_tx')[0]
    except RuntimeError:
        lat = su.read_snappy_product(high_res_geom, 'latitude_in')[0]
    try:
        lon = su.read_snappy_product(high_res_geom, 'longitude_tx')[0]
    except RuntimeError:
        lon = su.read_snappy_product(high_res_geom, 'longitude_in')[0]
    doy = date_time_utc.timetuple().tm_yday
    ftime = date_time_utc.hour + date_time_utc.minute/60.0
    cos_theta = incidence_angle_tilted(lat, lon, doy, ftime, stdlon=0, A_ZS=aspect, slope=slope)
    proj, gt = gu.raster_info(temp_dem_file)[0:2]
    temp_cos_theta_file = pth.splitext(temp_dem_file)[0] + '_cos_theta.tif'
    fp = gu.save_image(cos_theta, gt, proj, temp_cos_theta_file)
    fp = None
    slope = None
    aspect = None
    cos_theta = None

    print('INFO: Preparing high-resolution data...')
    # Combine all high-resolution data into one virtual raster
    temp_file = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    temp_refl_file = temp_file.name
    temp_file.close()
    su.copy_bands_to_file(sentinel_2_reflectance, temp_refl_file)
    vrt_filename = pth.splitext(temp_refl_file)[0]+".vrt"
    fp = gu.merge_raster_layers([temp_refl_file, temp_dem_file, temp_cos_theta_file],
                                vrt_filename, separate=True)
    fp = None
    high_res_filename = vrt_filename

    # Save low resolution files as geotiffs
    temp_file = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    temp_lst_file = temp_file.name
    temp_file.close()
    su.copy_bands_to_file(sentinel_3_lst, temp_lst_file, ["LST"])
    temp_file = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    temp_mask_file = temp_file.name
    temp_file.close()
    su.copy_bands_to_file(lst_quality_mask, temp_mask_file)

    # Set options of the disaggregator
    flags = [int(i) for i in lst_good_quality_flags.split(",")]
    dms_options =\
        {"highResFiles": [high_res_filename],
         "lowResFiles": [temp_lst_file],
         "lowResQualityFiles": [temp_mask_file],
         "lowResGoodQualityFlags": flags,
         "cvHomogeneityThreshold": cv_homogeneity_threshold,
         "movingWindowSize": moving_window_size,
         "disaggregatingTemperature":  True,
         "baggingRegressorOpt":        {"n_jobs": parallel_jobs, "n_estimators": 30,
                                        "max_samples": 0.8, "max_features": 0.8}}
    disaggregator = DecisionTreeSharpener(**dms_options)

    # Do the sharpening
    print("INFO: Training regressor...")
    disaggregator.trainSharpener()
    print("INFO: Sharpening...")
    downscaled_file = disaggregator.applySharpener(high_res_filename, temp_lst_file)
    print("INFO: Residual analysis...")
    residual_image, corrected_image = disaggregator.residualAnalysis(downscaled_file,
                                                                     temp_lst_file,
                                                                     temp_mask_file,
                                                                     doCorrection=True)
    # Save the sharpened file
    band = {"band_name": "sharpened_LST", "description": "Sharpened Sentinel-3 LST", "unit": "K",
            "band_data": corrected_image.GetRasterBand(1).ReadAsArray()}
    geo_coding = su.get_product_info(sentinel_2_reflectance)[1]
    su.write_snappy_product(output, [band], "sharpenedLST", geo_coding)

    # Clean up
    try:
        os.remove(temp_dem_file)
        os.remove(temp_aspect_file)
        os.remove(temp_slope_file)
        os.remove(temp_cos_theta_file)
        os.remove(temp_refl_file)
        os.remove(temp_lst_file)
        os.remove(temp_mask_file)
    except Exception:
        pass


def declination_angle(doy):
    ''' Calculates the Earth declination angle

    Parameters
    ----------
    doy : float or int
        day of the year

    Returns
    -------
    declination : float
        Declination angle (radians)
    '''
    declination = np.radians(23.45) * np.sin((2.0 * np.pi * doy / 365.0) - 1.39)

    return declination


def hour_angle(ftime, declination, lon, stdlon=0):
    '''Calculates the hour angle

    Parameters
    ----------
    ftime : float
        Time of the day (decimal hours)
    declination : float
        Declination angle (radians)
    lon : float
        longitude of the site (degrees).
    stdlon : float
        Longitude of the standard meridian that represent the ftime time zone

    Returns
    w : float
        hour angle (radians)
    '''

    EOT = 0.258 * np.cos(declination) - 7.416 * np.sin(declination) - \
          3.648 * np.cos(2.0 * declination) - 9.228 * np.sin(2.0 * declination)
    LC = (stdlon - lon) / 15.
    time_corr = (-EOT / 60.) + LC
    solar_time = ftime - time_corr
    # Get the hour angle
    w = np.radians((12.0 - solar_time) * 15.)

    return w


def incidence_angle_tilted(lat, lon, doy, ftime, stdlon=0, A_ZS=0, slope=0):
    ''' Calculates the incidence solar angle over a tilted flat surface

    Parameters
    ----------
    lat :  float or array
        latitude (degrees)
    lon :  float or array
        longitude (degrees)
    doy : int
        day of the year
    ftime : float
        Time of the day (decimal hours)
    stdlon : float
        Longitude of the standard meridian that represent the ftime time zone
    A_ZS : float or array
        surface azimuth angle, measured clockwise from north (degrees)
    slope : float or array
        slope angle (degrees)

    Returns
    -------
    cos_theta_i : float or array
        cosine of the incidence angle
    '''

    # Get the dclination and hour angle
    delta = declination_angle(doy)
    omega = hour_angle(ftime, delta, lon, stdlon=stdlon)

    # Convert remaining angles into radians
    lat, A_ZS, slope = map(np.radians, [lat, A_ZS, slope])

    cos_theta_i = (np.sin(delta) * np.sin(lat) * np.cos(slope)
                   + np.sin(delta) * np.cos(lat) * np.sin(slope) * np.cos(A_ZS)
                   + np.cos(delta) * np.cos(lat) * np.cos(slope) * np.cos(omega)
                   - np.cos(delta) * np.sin(lat) * np.sin(slope) * np.cos(A_ZS) * np.cos(omega)
                   - np.cos(delta) * np.sin(slope) * np.sin(A_ZS) * np.sin(omega))

    return cos_theta_i


if __name__ == "__main__":
    #try:
    main()
    #except Exception as e:
    #    print("ERROR:" + str(e))
