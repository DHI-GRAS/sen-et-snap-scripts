import click
import numpy as np

from pyTSEB import TSEB

import snappy_utils as su
import snappy


@click.command()
@click.option('--elevation_map', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--elevation_band', required=True)
@click.option('--ecmwf_data_file', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--date_time_UTC', required=True, type=click.DateTime(formats=['%Y-%m-%d %H:%M']))
@click.option('--prepare_temperature',required=True, type=click.BOOL)
@click.option('--prepare_vapour_pressure',required=True, type=click.BOOL)
@click.option('--prepare_air_pressure',required=True, type=click.BOOL)
@click.option('--prepare_wind_speed',required=True, type=click.BOOL)
@click.option('--prepare_clear_sky_solar_radiation',required=True, type=click.BOOL)
@click.option('--prepare_daily_solar_irradiance',required=True, type=click.BOOL)
@click.option('--output_file', required=True, type=click.Path(dir_okay=False, exists=False))
def main(elevation_map, elevation_band, ecmwf_data_file, date_time_UTC, prepare_temperature,
        prepare_vapour_pressure, prepare_air_pressure, prepare_wind_speed
        prepare_clear_sky_solar_radiation, prepare_daily_solar_irradiance,output_file):

    # Read the required data
    elevation_band = su.read_snappy_product(elevation_map, elevation_band)
    # TO BE IMPLEMENTED


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
