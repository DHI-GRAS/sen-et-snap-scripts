import os
from datetime import datetime, timedelta

import click

from find_sentinel_images import find_sentinel_images


@click.command()
@click.option('--aoi_geojson', required=True, type=click.Path(dir_okay=False, exists=True))
@click.option('--start_date', required=True, type=click.DateTime(formats=['%Y%m%d']))
@click.option('--end_date', required=True, type=click.DateTime(formats=['%Y%m%d']))
@click.option('--platform', required=True, type=click.Choice(choices=['Sentinel-2', 'Sentinel-3']))
@click.option('--username', required=True)
@click.option('--password', required=True)
@click.option('--download_path', required=True, type=click.Path(file_okay=False))
@click.option('--download_images', type=click.BOOL)
@click.option('--cloud_cover_percentage', required=True, type=click.IntRange(min=0, max=100))
@click.option('--limit_tiles', required=False)
def main(aoi_geojson, start_date, end_date, platform, username, password, download_path,
         download_images, cloud_cover_percentage, limit_tiles):

    cloud_cover_percentage = "[0 TO "+str(cloud_cover_percentage)+"]"
    start_date = start_date.isoformat() + "Z"
    end_date = end_date + timedelta(hours=23, minutes=59, seconds=59)
    end_date = end_date.isoformat() + "Z"
    if not limit_tiles or limit_tiles == '$limit_tiles':
        limit_tiles = []
    else:
        limit_tiles = limit_tiles.replace(" ", "")
        limit_tiles = limit_tiles.upper()
        limit_tiles = limit_tiles.split(",")

    # Set platform specific settings
    other_search_keywords = {}
    if platform == "Sentinel-2":
        other_search_keywords = {"cloudcoverpercentage": cloud_cover_percentage,
                                 "producttype": "S2MSI2A"}
    elif platform == "Sentinel-3":
        other_search_keywords = {"instrumentshortname": "SLSTR",
                                 "productlevel": "L2"}

    # Download the images
    products = find_sentinel_images(aoi_geojson, start_date,
                                    end_date, platform, username,
                                    password, "", download_path, download=download_images,
                                    other_search_keywords=other_search_keywords,
                                    limit_to_tiles=limit_tiles)

    now = datetime.today().strftime("%Y%m%d%H%M%S")
    with open(os.path.join(download_path, "sentinel_data_download_"+now+".txt"), "w") as fp:
        for product in products:
            print(product)
            fp.write(str(product))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:" + str(e))
