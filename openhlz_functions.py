# -*- coding: utf-8 -*-

"""
/***************************************************************************
 OpenHLZ
                                 A QGIS plugin
 Open-source HLZ Identification Plugin
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-08-13
        copyright            : (C) 2023 by John Erskine
        email                : erskine.john.c@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import qgis.core
# Import statements
from pyproj import Proj, transform
import json
from qgis import processing
from qgis import *
from qgis._core import *
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtCore import QUrl


def getJson(aoi_layer, scratch_folder, project_coordinate_system_name):
    """
    Function to get JSON file return for either DEM or LULC

    Returns JSON files for 1m and 10m data
    """

    # Get bounding box
    extent_var = aoi_layer.extent()
    extent_array = [extent_var.xMinimum(), extent_var.yMinimum(), extent_var.xMaximum(), extent_var.yMaximum()]
    input_projection = Proj(project_coordinate_system_name)
    output_projection = Proj('epsg:4326')
    min_x_proj, min_y_proj = transform(input_projection, output_projection, extent_array[0], extent_array[1])
    max_x_proj, max_y_proj = transform(input_projection, output_projection, extent_array[2], extent_array[3])
    url_bbox = str(min_y_proj) + ',' + str(min_x_proj) + ',' + str(max_y_proj) + ',' + str(max_x_proj)

    # Get json return for 1m DEM
    url = 'https://tnmaccess.nationalmap.gov/api/v1/products?bbox=' + url_bbox + \
          '&datasets=Digital+Elevation+Model+(DEM)+1+meter&prodFormats=GeoTIFF&outputFormat=json'
    qurl = QUrl(url)
    output_json_filename_1m = scratch_folder + '/json_1m.json'
    request = QNetworkRequest(qurl)
    network_access_manager = QgsNetworkAccessManager()
    response_1m = network_access_manager.blockingGet(request)
    content = response_1m.content()
    open(output_json_filename_1m, "wb").write(content)
    temp_file = open(output_json_filename_1m, )
    json_1m = json.load(temp_file)
    temp_file.close()

    # Get json return for 1/3 arc-second (10m) data
    url = 'https://tnmaccess.nationalmap.gov/api/v1/products?bbox=' + url_bbox + \
          ('&datasets=National%20Elevation%20Dataset%20('
           'NED)%201%20arc-second&prodFormats=GeoTIFF&outputFormat=json')
    qurl = QUrl(url)
    output_json_filename_10m = scratch_folder + '/json_10m.json'
    request = QNetworkRequest(qurl)
    network_access_manager = QgsNetworkAccessManager()
    response_10m = network_access_manager.blockingGet(request)
    content = response_10m.content()
    open(output_json_filename_10m, "wb").write(content)
    temp_file_10m = open(output_json_filename_10m, )
    json_10m = json.load(temp_file_10m)
    temp_file_10m.close()

    return json_1m, json_10m


def downloadDem(i, json_file, scratch_folder, using_10m_data):
    """
    Function to download DEM data based on input location. Will first try 1m, then will try 10m if no 1m

    Returns filename of saved DEM raster
    """

    # Download 1m data if not using 10m data
    if not using_10m_data:
        temp_dict = json_file['items'][i]
        download_url = QUrl(temp_dict['downloadURL'])
        request = QNetworkRequest(download_url)
        output_filename = scratch_folder + '/dem_1m_' + str(i) + '.tif'
        network_access_manager = QgsNetworkAccessManager()
        response = network_access_manager.blockingGet(request)
        content = response.content()
        open(output_filename, "wb").write(content)
        temp_dem = open(output_filename, )
        temp_dem.close()
        return output_filename

    # Else download 10m data
    else:
        temp_dict = json_file['items'][i]
        download_url = QUrl(temp_dict['downloadURL'])
        request = QNetworkRequest(download_url)
        output_filename = scratch_folder + '/dem_10m_' + str(i) + '.tif'
        network_access_manager = QgsNetworkAccessManager()
        response = network_access_manager.blockingGet(request)
        content = response.content()
        open(output_filename, "wb").write(content)
        temp_dem = open(output_filename, )
        temp_dem.close()
        return output_filename


def downloadLULC(i, utm_zones, scratch_folder):
    """
    Function to download LULC data based on current location

    Returns filename of saved LULC raster
    """

    # Download data based on whichever UTM zone the aoi is within
    zone = utm_zones[i]
    zone_id = str(zone[0]) + zone[1]
    output_filename = scratch_folder + '/' + zone_id + ".tif"
    url = 'https://lulctimeseries.blob.core.windows.net/lulctimeseriespublic/lc2021/' + zone_id + \
          '_20210101-20220101.tif'
    qurl = QUrl(url)
    request = QNetworkRequest(qurl)
    network_access_manager = QgsNetworkAccessManager()
    response = network_access_manager.blockingGet(request)
    content = response.content()
    open(output_filename, "wb").write(content)
    temp_lulc = open(output_filename, )
    temp_lulc.close()
    return output_filename


def mosaicAndClipRasters(output_dem_filenames, output_lulc_filenames, aoi_layer, scratch_folder, feedback):
    """
    Function to mosaic and clip LULC and DEM rasters based on input AOI
    """

    # Mosaic dem data
    feedback.setProgressText('Mosaicing DEM Data')
    output_dem_filename = scratch_folder + '/dem_mosaic.tif'
    mosaic_parameters = ['', '-o', output_dem_filename]
    for i in range(len(output_dem_filenames)):
        mosaic_parameters.append(output_dem_filenames[i])
    processing.run("gdal:merge", {'INPUT': output_dem_filenames,
                                  'PCT': False, 'SEPARATE': False, 'NODATA_INPUT': None, 'NODATA_OUTPUT': None,
                                  'OPTIONS': '', 'EXTRA': '', 'DATA_TYPE': 5,
                                  'OUTPUT': scratch_folder + '/dem_mosaic.tif'})

    # Mosaic lulc data
    feedback.setProgressText('Mosaicing LULC Data')
    output_lulc_filename = scratch_folder + '/lulc_mosaic.tif'
    mosaic_parameters = ['', '-o', output_lulc_filename]
    for i in range(len(output_lulc_filenames)):
        mosaic_parameters.append(output_lulc_filenames[i])
    processing.run("gdal:merge", {'INPUT': output_lulc_filenames,
                                  'PCT': False, 'SEPARATE': False, 'NODATA_INPUT': None, 'NODATA_OUTPUT': None,
                                  'OPTIONS': '', 'EXTRA': '', 'DATA_TYPE': 0,
                                  'OUTPUT': scratch_folder + '/lulc_mosaic.tif'})

    # Clip and reproject dem and lulc layers
    feedback.setProgressText('Clipping DEM Data')
    processing.run("gdal:cliprasterbymasklayer", {'INPUT': scratch_folder + '/dem_mosaic.tif', 'MASK': aoi_layer,
                                                  'SOURCE_CRS': None, 'TARGET_CRS': aoi_layer.crs().authid(),
                                                  'TARGET_EXTENT': None,
                                                  'NODATA': None, 'ALPHA_BAND': False,
                                                  'CROP_TO_CUTLINE': True, 'KEEP_RESOLUTION': False,
                                                  'SET_RESOLUTION': False, 'X_RESOLUTION': None,
                                                  'Y_RESOLUTION': None, 'MULTITHREADING': False,
                                                  'OPTIONS': '', 'DATA_TYPE': 6, 'EXTRA': '',
                                                  'OUTPUT': scratch_folder + '/projected_dem.tif'})

    feedback.setProgressText('Clipping LULC Data')
    processing.run("gdal:cliprasterbymasklayer", {'INPUT': scratch_folder + '/lulc_mosaic.tif', 'MASK': aoi_layer,
                                                  'SOURCE_CRS': None, 'TARGET_CRS': aoi_layer.crs().authid(),
                                                  'TARGET_EXTENT': None,
                                                  'NODATA': None, 'ALPHA_BAND': False,
                                                  'CROP_TO_CUTLINE': True, 'KEEP_RESOLUTION': False,
                                                  'SET_RESOLUTION': False, 'X_RESOLUTION': None,
                                                  'Y_RESOLUTION': None, 'MULTITHREADING': False,
                                                  'OPTIONS': '', 'DATA_TYPE': 0, 'EXTRA': '',
                                                  'OUTPUT': scratch_folder + '/projected_lulc.tif'})


def generateHlsRaster(output, projected_dem, slope_caution, slope_limit, project_coordinate_system,
                      style_path, instance, scratch_folder):
    """
    Function to generate HLS raster based on slope and LULC constraints (see README.md on GitHub for more info on
    methodology).
    """
    # Calculate slope raster
    processing.run("gdal:slope", {'INPUT': projected_dem, 'BAND': 1, 'SCALE': 1, 'AS_PERCENT': False,
                                  'COMPUTE_EDGES': False, 'ZEVENBERGEN': False, 'OPTIONS': '', 'EXTRA': '',
                                  'OUTPUT': scratch_folder + '/slope_raster.tif'})

    # Reclassify slope and LULC rasters
    processing.run("qgis:rastercalculator", {'EXPRESSION': '"slope_raster@1" < ' + str(slope_caution),
                                             'LAYERS': [scratch_folder + '/slope_raster.tif'],
                                             'CELLSIZE': 0, 'EXTENT': None, 'CRS': project_coordinate_system,
                                             'OUTPUT': scratch_folder + '/slope_caution.tif'})
    processing.run("qgis:rastercalculator", {'EXPRESSION': '"slope_raster@1" < ' + str(slope_limit),
                                             'LAYERS': [scratch_folder + '/slope_raster.tif'],
                                             'CELLSIZE': 0, 'EXTENT': None, 'CRS': project_coordinate_system,
                                             'OUTPUT': scratch_folder + '/slope_limit.tif'})
    processing.run("qgis:rastercalculator", {'EXPRESSION': '"slope_limit@1" + "slope_caution@1"',
                                             'LAYERS': [scratch_folder + '/slope_limit.tif',
                                                        scratch_folder + '/slope_caution.tif'],
                                             'CELLSIZE': 0, 'EXTENT': None, 'CRS': project_coordinate_system,
                                             'OUTPUT': scratch_folder + '/slope_reclass.tif'})
    os.remove(scratch_folder + '/slope_raster.tif')
    os.remove(scratch_folder + '/slope_limit.tif')
    os.remove(scratch_folder + '/slope_caution.tif')

    processing.run("qgis:rastercalculator", {'EXPRESSION': '("projected_lulc@1" = 5) or ("projected_lulc@1" = 11)',
                                             'LAYERS': [scratch_folder + '/projected_lulc.tif'],
                                             'CELLSIZE': 0, 'EXTENT': None, 'CRS': project_coordinate_system,
                                             'OUTPUT': scratch_folder + '/lulc_reclass.tif'})
    os.remove(scratch_folder + '/projected_lulc.tif')

    # Generate HLS
    hls_raster = processing.run("qgis:rastercalculator", {'EXPRESSION': '"lulc_reclass@1" * "slope_reclass@1',
                                                          'LAYERS': [scratch_folder + '/lulc_reclass.tif',
                                                                     scratch_folder + '/slope_reclass.tif'],
                                                          'CELLSIZE': 0, 'EXTENT': None,
                                                          'CRS': project_coordinate_system,
                                                          'OUTPUT': output})['OUTPUT']
    os.remove(scratch_folder + '/lulc_reclass.tif')
    os.remove(scratch_folder + '/slope_reclass.tif')

    # Add raster layer to map
    hls_layer = qgis.core.QgsRasterLayer(hls_raster, 'HLS Overlay')
    instance.addMapLayer(hls_layer)

    # Add layer style and trigger repaint
    hls_layer.loadNamedStyle(style_path)
    hls_layer.triggerRepaint()

    return hls_raster


def identifyHlzs(output, hls_raster, tdp_diameter, project_coordinate_system, style_path, instance, scratch_folder):
    """
    Function to identify possible HLZs based on criteria and HLS raster
    """
    # Convert raster (only values of 1 or 2) to polygons
    processing.run("gdal:polygonize", {'INPUT': hls_raster, 'BAND': 1, 'FIELD': 'DN',
                                       'EIGHT_CONNECTEDNESS': False, 'EXTRA': '',
                                       'OUTPUT': scratch_folder + '/pixel_polygons.shp'})

    processing.run("native:reprojectlayer", {'INPUT': scratch_folder + '/pixel_polygons.shp',
                                             'TARGET_CRS': project_coordinate_system,
                                             'OPERATION': '+proj=noop',
                                             'OUTPUT': scratch_folder + '/hls_pixels_polygons_projected.shp'})

    selectAndExportFeatures(scratch_folder + '/hls_pixels_polygons_projected.shp',
                            '("DN" = 1) or ("DN" = 2)',
                            scratch_folder + '/selected_pixel_polygons.shp')

    # Dissolve polygons
    hls_dissolve = \
        processing.run("native:dissolve", {'INPUT': scratch_folder + '/selected_pixel_polygons.shp', 'FIELD': [],
                                           'SEPARATE_DISJOINT': True, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
    hls_dissolve_geometry = \
        processing.run("qgis:exportaddgeometrycolumns", {'INPUT': hls_dissolve, 'CALC_METHOD': 0,
                                                         'OUTPUT': scratch_folder + '/hls_dissolve_geometry.shp'})[
            'OUTPUT']

    # Select polygons based on area
    selectAndExportFeatures(scratch_folder + '/hls_dissolve_geometry.shp',
                            '"area" > ' + str(tdp_diameter * tdp_diameter),
                            scratch_folder + '/large_enough_areas.shp')

    # Calculate centroids
    output_hlzs = processing.run("native:centroids", {'INPUT': scratch_folder + '/large_enough_areas.shp',
                                                      'ALL_PARTS': True, 'OUTPUT': output})['OUTPUT']
    # Add raster layer to map
    hlz_layer = qgis.core.QgsVectorLayer(output_hlzs, 'Possible HLZs')
    instance.addMapLayer(hlz_layer)

    # Add layer style and trigger repaint
    hlz_layer.loadNamedStyle(style_path)
    hlz_layer.triggerRepaint()

    return output_hlzs


def selectAndExportFeatures(input_filename, input_expression, output_filename):
    """
    Function to select features within an input file based on an input expression and then export them to a new file
    """
    temp_layer = qgis.core.QgsVectorLayer(input_filename, 'temp_layer')
    temp_layer.selectByExpression(input_expression, QgsVectorLayer.SetSelection)
    QgsVectorFileWriter.writeAsVectorFormat(temp_layer, output_filename, 'utf-8', driverName='ESRI Shapefile',
                                            onlySelected=True)