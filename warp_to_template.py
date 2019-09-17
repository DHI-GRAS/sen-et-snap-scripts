import click
import tempfile
import os

import ecmwf_utils as eu
import snappy_utils as su


@click.command()
@click.option('--source', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--template', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--resample_algorithm', required=True, default='cubicspline')
@click.option('--output', required=True, type=click.Path(dir_okay=False, exists=False))
def main(source, template, output, resample_algorithm):

    # Save source and template to GeoTIFF becasue it will need to be read by GDAL
    temp_file = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    temp_source_path = temp_file.name
    temp_file.close()
    su.copy_bands_to_file(source, temp_source_path)
    temp_file = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    temp_template_path = temp_file.name
    temp_file.close()
    su.copy_bands_to_file(template, temp_template_path)

    # Wrap the source based on tamplate
    wraped = eu.resample_with_gdalwarp(temp_source_path, temp_template_path, resample_algorithm)

    # Save with snappy
    name, geo_coding = su.get_product_info(template)[0:2]
    bands = su.get_bands_info(source)
    for i, band in enumerate(bands):
        band['band_data'] = wraped.GetRasterBand(i+1).ReadAsArray()
    su.write_snappy_product(output, bands, name, geo_coding)

    # Clean up
    try:
        os.remove(temp_source_path)
        os.remove(temp_template_path)
    except Exception:
        pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
