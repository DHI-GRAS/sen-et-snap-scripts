import os
from datetime import datetime

import click

from find_sentinel_images import find_sentinel_images


@click.command
@click.option('--aoi_geojson', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--start_date', required=True, type=click.DateTime(formats=('%Y%m%d')))
@click.option('--end_date', required=True, type=click.DateTime(formats=('%Y%m%d')))
@click.option('--platform', required=True, type=click.Choice(choices=('Sentinel-2', 'Sentinel-3')))
@click.option('--username', required=True)
@click.option('--password', required=True)
@click.option('--download_path', required=True, type=click.Path(file_okay=False))
@click.option('--download_images', type=click.BOOL)
@click.option('--cloud_cover_percentage', required=True, type=click.IntRange(min=0, max=100))
def main(aoi_geojson, start_date, end_date, platform, username, password, download_path,
         download_images, cloud_cover_percentage):

    cloud_cover_percentage = "[0 TO "+str(cloud_cover_percentage)+"]"

    # Set platform specific settings
    other_search_keywords = {}
    if platform == "Sentinel-2":
        other_search_keywords = {"cloudcoverpercentage": cloud_cover_percentage,
                                 "producttype": "S2MSI2A"}
    elif platform == "Sentinel-3":
        other_search_keywords = {"instrumentshortname": "SLSTR",
                                 "productlevel": "L2"}

    # Download the images
    products = find_sentinel_images(aoi_geojson, start_date, end_date, platform, username,
                                    password, "", download_path, download=download_images,
                                    other_search_keywords=other_search_keywords)

    print(products)
    now = datetime.today().strftime("%Y%m%d%H%M%S")
    with open(os.path.join(download_path, "sentinel_data_download_"+now+".txt"), "w") as fp:
        for product in products:
            fp.write(product)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
