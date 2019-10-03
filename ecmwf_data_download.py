import os
import click

from ecmwf_utils import download_CDS_data


@click.command()
@click.option('--area', required=False)
@click.option('--start_date', required=True)
@click.option('--end_date', required=True)
@click.option('--download_path', required=True, type=click.Path(file_okay=False))
@click.option('--download_temperature', required=True, type=click.BOOL)
@click.option('--download_dewpoint', required=True, type=click.BOOL)
@click.option('--download_pressure', required=True, type=click.BOOL)
@click.option('--download_wind_speed', required=True, type=click.BOOL)
@click.option('--download_clear_sky_solar_radiation', required=True, type=click.BOOL)
@click.option('--download_solar_radiation', required=True, type=click.BOOL)
@click.option('--overwrite', required=True, type=click.BOOL)
def main(area, start_date, end_date, download_path, download_pressure,
         download_temperature, download_dewpoint, download_wind_speed,
         download_clear_sky_solar_radiation, download_solar_radiation, overwrite):
        fields = []
        if download_temperature:
            fields.extend(['2m_temperature', 'z', '2m_dewpoint_temperature', 'surface_pressure'])
        if download_dewpoint and '2m_dewpoint_temperature' not in fields:
            fields.append('2m_dewpoint_temperature')
        if download_pressure and 'surface_pressure' not in fields:
            fields.append('surface_pressure')
        if download_wind_speed:
            fields.extend(['100m_v_component_of_wind', '100m_u_component_of_wind'])
        if download_clear_sky_solar_radiation:
            fields.append("surface_solar_radiation_downward_clear_sky")
        if download_solar_radiation:
            fields.append('surface_solar_radiation_downwards')
        
        download_CDS_data(start_date, end_date, fields, download_path, overwrite, area)
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
