# @author Seth Younger
# @email seth.younger@noaa.gov

#!/usr/bin/env python3
"""
Majority Vegetation type analysis from NLCD land cover data

This script reads hydrofabric geopackage files and uses HyRivers nlcd functionality to
calculate majority NLCD land cover vegetation type in USGS landcover codes.

IMPORTANT: Data availability varies by region:
- L48 (CONUS): Years 2001, 2004, 2006, 2008, 2011, 2013, 2016, 2019, 2021 available
- AK (Alaska): Limited years 2001, 2011, 2016 available  
- HI (Hawaii): Only 2001 available (land cover)
  * HI data is stored as RGB raster - script automatically converts RGB colors to NLCD codes
- PR (Puerto Rico): Only 2001 available for land cover and impervious
  * PR data is stored as RGB raster - script automatically converts RGB colors to NLCD codes

Usage:
    python nlcd_vegtyp.py --help

    python nlcd_vegtyp.py /path/to/directory/with/gpkg/files
    python nlcd_vegtyp.py /path/to/pr/files --region PR --year 2001

Requirements:
    - geopandas
    - pandas
    - numpy
    - pygeohydro
    - xarray
"""

import os
import sys
import argparse
from pathlib import Path
import time
import sqlite3
import warnings
from typing import Dict, Any

import geopandas as gpd
import pandas as pd
import numpy as np
from pygeohydro import nlcd
import xarray as xr


def convert_rgb_to_nlcd_classes(rgb_data: np.ndarray) -> np.ndarray:
    """
    Convert RGB NLCD data to classified NLCD codes.
    Uses actual RGB colors from Puerto Rico NLCD data.
    
    Parameters:
    -----------
    rgb_data : np.ndarray
        RGB data array with shape (3, height, width) or (height, width, 3)
        
    Returns:
    --------
    np.ndarray
        2D array with NLCD class codes
    """
    
    # Actual RGB colors from Puerto Rico NLCD data
    nlcd_rgb_colors = {
        # Background/No data
        (0, 0, 0): 0,          # No data (black)
        
        # Water
        (71, 107, 161): 11,    # Open Water (blue)
        
        # Developed
        (222, 202, 202): 21,   # Developed, Open Space (light pink)
        (217, 148, 130): 22,   # Developed, Low Intensity (pink)
        (238, 0, 0): 23,       # Developed, Medium Intensity (bright red)
        (171, 0, 0): 24,       # Developed, High Intensity (dark red)
        
        # Barren
        (179, 174, 163): 31,   # Barren Land (gray)
        
        # Forest
        (28, 99, 48): 42,      # Evergreen Forest (dark green)
        
        # Shrubland  
        (204, 186, 125): 52,   # Shrub/Scrub (tan)
        
        # Herbaceous
        (220, 217, 61): 71,    # Grassland/Herbaceous (yellow-green)
        
        # Planted/Cultivated
        (227, 227, 194): 81,   # Pasture/Hay (light tan)
        (171, 112, 40): 82,    # Cultivated Crops (brown)
        
        # Wetlands
        (186, 217, 235): 90,   # Woody Wetlands (light blue)
        (112, 163, 186): 95,   # Emergent Herbaceous Wetlands (blue-gray)
    }
    
    # Handle different array shapes
    if rgb_data.shape[0] == 3:
        # Shape (3, height, width) - channels first
        height, width = rgb_data.shape[1], rgb_data.shape[2]
        r_band, g_band, b_band = rgb_data[0], rgb_data[1], rgb_data[2]
    elif rgb_data.shape[-1] == 3:
        # Shape (height, width, 3) - channels last
        height, width = rgb_data.shape[0], rgb_data.shape[1]
        r_band, g_band, b_band = rgb_data[:,:,0], rgb_data[:,:,1], rgb_data[:,:,2]
    else:
        raise ValueError(f"Unexpected RGB data shape: {rgb_data.shape}")
    
    nlcd_classes = np.zeros((height, width), dtype=np.uint8)
    
    # Process each pixel
    for i in range(height):
        for j in range(width):
            r, g, b = int(r_band[i, j]), int(g_band[i, j]), int(b_band[i, j])
            rgb_tuple = (r, g, b)
            
            # Look for exact match first
            if rgb_tuple in nlcd_rgb_colors:
                nlcd_classes[i, j] = nlcd_rgb_colors[rgb_tuple]
            else:
                # Find closest color match
                min_distance = float('inf')
                closest_class = 0
                
                for color, class_code in nlcd_rgb_colors.items():
                    if class_code == 0:  # Skip no-data
                        continue
                    distance = ((r - color[0])**2 + (g - color[1])**2 + (b - color[2])**2)**0.5
                    if distance < min_distance:
                        min_distance = distance
                        closest_class = class_code
                
                # Only assign if reasonably close (distance < 30)
                if min_distance < 30 and closest_class > 0:
                    nlcd_classes[i, j] = closest_class
    
    return nlcd_classes


def calculate_pr_rgb_statistics(cover_da) -> Dict:
    """
    Calculate cover statistics for PR/HI RGB NLCD data.
    
    Parameters:
    -----------
    cover_da : xarray.DataArray
        Cover data array (RGB or multi-band)
        
    Returns:
    --------
    dict
        Dictionary with class codes as keys and percentages as values
    """
    import numpy as np
    
    # Get the data values
    if hasattr(cover_da, 'values'):
        data = cover_da.values
    else:
        data = np.array(cover_da)
    
    # Check if this is RGB data (3 bands)
    if data.ndim == 3 and data.shape[0] == 3:
        # Convert RGB to NLCD classes
        nlcd_classes = convert_rgb_to_nlcd_classes(data)
        data = nlcd_classes
    elif data.ndim == 3:
        # Fallback to manual handling for multi-band data
        data = data.flatten()
    else:
        # Single band or flattened data
        data = data.flatten()
    
    # Calculate statistics from classified data
    if data.ndim == 2:
        data = data.flatten()
    
    # Remove common no-data values
    nodata_values = [0, 127, 255]
    valid_data = data[~np.isin(data, nodata_values)]
    
    if len(valid_data) == 0:
        return {}
    
    # Calculate class percentages
    unique_values, counts = np.unique(valid_data, return_counts=True)
    total_valid = len(valid_data)
    
    class_stats = {}
    for value, count in zip(unique_values, counts):
        percentage = (count / total_valid) * 100
        class_stats[int(value)] = percentage
    
    return class_stats

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

def get_domain_nlcd_config(region: str, year: int) -> Dict[str, Any]:
    """
    Get the appropriate NLCD configuration for a given region and year.
    
    Parameters:
    -----------
    region : str
        Region code ('L48', 'AK', 'HI', 'PR')
    year : int
        Requested year
        
    Returns:
    --------
    dict
        Configuration dictionary with years and any special parameters
        
    Raises:
    -------
    ValueError
        If the year/region combination is not supported
    """
    # Define available data by region
    region_availability = {
        'L48': {
            'years': [2001, 2004, 2006, 2008, 2011, 2013, 2016, 2019, 2021],
            'layers': ['cover', 'impervious', 'canopy', 'descriptor'],
            'default_config': lambda y: {'cover': [y], 'impervious': [y], 'canopy': [y]}
        },
        'AK': {
            'years': [2001, 2011, 2016],  # Alaska has limited years - only these are actually available
            'layers': ['cover', 'impervious', 'canopy', 'descriptor'],
            'default_config': lambda y: {'cover': [y], 'impervious': [y], 'canopy': [y]}
        },
        'HI': {
            'years': [2001],  # Hawaii very limited
            'layers': ['cover', 'impervious'],
            'default_config': lambda y: {'cover': [y], 'impervious': [y]}
        },
        'PR': {
            'years': [2001],  # Puerto Rico very limited
            'layers': ['cover', 'impervious'],  # No descriptor or recent years
            'default_config': lambda y: {'cover': [y], 'impervious': [y]}
        }
    }
    
    if region not in region_availability:
        raise ValueError(f"Unsupported region: {region}. Supported regions: {list(region_availability.keys())}")
    
    region_info = region_availability[region]
    
    if year not in region_info['years']:
        available_years = ', '.join(map(str, region_info['years']))
        raise ValueError(
            f"Year {year} is not available for region {region}. "
            f"Available years for {region}: {available_years}"
        )
    
    # Get the configuration for this region/year
    years_config = region_info['default_config'](year)
    
    return {
        'years': years_config,
        'region': region
    }


def read_geopackage_and_calculate_nlcd_majority(
    geopackage_path: str, 
    year: int = 2021,
    region: str = 'L48'
) -> gpd.GeoDataFrame:
    """
    Read a geopackage with multiple polygons and calculate the majority NLCD cover 
    for each polygon using HyRiver toolset.
    
    Parameters:
    -----------
    geopackage_path : str
        Path to the geopackage file (SQLite database)
    year : int, default 2021
        Year of NLCD data to use. Available years vary by region:
        - L48: 2001, 2004, 2006, 2008, 2011, 2013, 2016, 2019, 2021
        - AK: 2001, 2011, 2016
        - HI: 2001 only
        - PR: 2001 only
    region : str, default 'L48'
        Region in the US ('L48' for CONUS, 'HI' for Hawaii, 'AK' for Alaska, 'PR' for Puerto Rico)
    
    Returns:
    --------
    geopandas.GeoDataFrame
        Original GeoDataFrame with additional columns for majority land cover class,
        percentage of majority class, and cover statistics
    """
    
    # Get and validate the configuration for this region/year
    try:
        config = get_domain_nlcd_config(region, year)
        print(f"Using configuration for {region} region, year {year}")
    except ValueError as e:
        print(f"Configuration Error: {e}")
        raise
    
    # Read the geopackage from SQL database
    print(f"Reading geopackage from SQL database: {geopackage_path}")
    
    # For hydrofabric geopackages, try to load the 'divides' layer first
    # since that contains the polygon catchments we want to analyze
    try:
        # First, try to load the 'divides' layer (polygon catchments)
        gdf = gpd.read_file(geopackage_path, layer='divides')
        print(f"Loaded {len(gdf)} polygons from 'divides' layer")
    except Exception:
        try:
            # If no 'divides' layer, try the default layer
            gdf = gpd.read_file(geopackage_path)
            print(f"Loaded {len(gdf)} features from default layer")
            
            # Check if we have polygons
            geom_types = gdf.geometry.geom_type.value_counts()
            if 'Polygon' not in geom_types and 'MultiPolygon' not in geom_types:
                print(f"WARNING: No polygons found in default layer")
                print(f"   Geometry types: {geom_types.to_dict()}")
                print(f"   NLCD analysis requires polygon geometries")
                
                # Try to find a layer with polygons
                try:
                    import fiona
                    layers = fiona.listlayers(geopackage_path)
                    print(f"   Available layers: {layers}")
                    
                    for layer_name in layers:
                        try:
                            test_gdf = gpd.read_file(geopackage_path, layer=layer_name)
                            test_types = test_gdf.geometry.geom_type.value_counts()
                            if 'Polygon' in test_types or 'MultiPolygon' in test_types:
                                gdf = test_gdf
                                print(f"   Using layer '{layer_name}' which contains {test_types.get('Polygon', 0)} polygons")
                                break
                        except:
                            continue
                    else:
                        raise ValueError(f"No polygon layers found in geopackage. NLCD analysis requires polygon geometries.")
                except ImportError:
                    raise ValueError(f"No polygons in default layer and cannot check other layers. Install fiona to auto-detect polygon layers.")
                    
        except Exception as e:
            print(f"Error loading geopackage: {e}")
            raise
    print(f"CRS: {gdf.crs}")
    
    # Ensure the GeoDataFrame is in a geographic CRS (EPSG:4326) for HyRiver
    if gdf.crs != 'EPSG:4326':
        print("Converting CRS to EPSG:4326 for HyRiver compatibility...")
        gdf = gdf.to_crs('EPSG:4326')
    
    # Get NLCD data for all polygons using domain-specific configuration
    print(f"Fetching NLCD {year} data for all polygons...")
    
    # Add retry logic for service availability issues
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"Retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay...")
                import time
                time.sleep(retry_delay)
            
            nlcd_data = nlcd.nlcd_bygeom(
                geometry=gdf,
                resolution=30,  # 30m resolution (native NLCD resolution)
                years=config['years'],
                region=region,
                crs=4326
            )
            print(f"Successfully retrieved NLCD data")
            break  # Success, exit retry loop
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error fetching NLCD data (attempt {attempt + 1}): {error_msg}")
            
            # Check for service availability issues
            if "Service is currently not available" in error_msg or "WMS" in error_msg:
                if attempt < max_retries - 1:
                    print(f"Service appears unavailable. Will retry in {retry_delay} seconds...")
                    continue
                else:
                    print(f"Service unavailable after {max_retries} attempts. This is a temporary MRLC server issue.")
                    print(f"Please try again later when the MRLC WMS service is restored.")
                    print(f"Service URL: https://www.mrlc.gov/geoserver/mrlc_download/wms")
            elif region in ['HI', 'PR'] and year != 2001:
                print(f"Hint: {region} region only has data for 2001. Try --year 2001")
            
            if attempt == max_retries - 1:  # Last attempt failed
                raise
    
    # Initialize lists to store results
    majority_classes = []
    majority_percentages = []
    cover_stats_list = []
    
    print("Calculating majority land cover for each polygon...")
    
    # Process each polygon
    for idx, row in gdf.iterrows():
        try:
            # Get NLCD data for this polygon
            polygon_nlcd = nlcd_data[idx] if isinstance(nlcd_data, dict) else nlcd_data
            
            # Extract the cover data - handle year-specific variable names
            if f'cover_{year}' in polygon_nlcd:
                cover_da = polygon_nlcd[f'cover_{year}']
            elif 'cover' in polygon_nlcd:
                cover_da = polygon_nlcd['cover']
            else:
                # Find the first cover variable
                cover_vars = [var for var in polygon_nlcd.data_vars if 'cover' in var]
                if cover_vars:
                    cover_da = polygon_nlcd[cover_vars[0]]
                else:
                    raise ValueError(f"No cover variable found in NLCD data. Available variables: {list(polygon_nlcd.data_vars)}")
            
            # Calculate cover statistics
            try:
                if region in ['PR', 'HI']:
                    # Use the RGB-aware statistics function for Puerto Rico and Hawaii
                    stats = calculate_pr_rgb_statistics(cover_da)
                else:
                    # Use standard cover_statistics for other regions
                    stats = nlcd.cover_statistics(cover_da)
                
                # Create reverse mapping from names to codes (complete NLCD legend)
                name_to_code = {
                    # Water
                    'Open Water': 11,
                    'Perennial Ice/Snow': 12,
                    # Developed
                    'Developed, Open Space': 21,
                    'Developed, Low Intensity': 22,
                    'Developed, Medium Intensity': 23,
                    'Developed, High Intensity': 24,
                    'Developed High Intensity': 24,  # Alternative name format
                    # Barren
                    'Barren Land': 31,
                    'Barren Land (Rock/Sand/Clay)': 31,  # Full name format
                    # Forest
                    'Deciduous Forest': 41,
                    'Evergreen Forest': 42,
                    'Mixed Forest': 43,
                    # Shrubland
                    'Dwarf Scrub': 51,
                    'Shrub/Scrub': 52,
                    # Herbaceous
                    'Grassland/Herbaceous': 71,
                    'Sedge/Herbaceous': 72,
                    'Lichens': 73,
                    'Moss': 74,
                    # Planted/Cultivated
                    'Pasture/Hay': 81,
                    'Cultivated Crops': 82,
                    # Wetlands
                    'Woody Wetlands': 90,
                    'Emergent Herbaceous Wetlands': 95
                }
                
                # Handle different statistics formats
                if hasattr(stats, 'classes') and stats.classes:
                    # Standard pygeohydro statistics object
                    max_percentage = 0
                    majority_class = None
                    
                    for class_name, percentage in stats.classes.items():
                        if percentage > max_percentage:
                            max_percentage = percentage
                            majority_class = name_to_code.get(class_name, class_name)  # Convert to code
                    
                    majority_classes.append(majority_class)
                    majority_percentages.append(max_percentage)
                    cover_stats_list.append(stats.classes)
                    
                elif isinstance(stats, dict):
                    # Manual statistics (returns class codes directly)
                    max_percentage = 0
                    majority_class = None
                    
                    for class_code, percentage in stats.items():
                        if percentage > max_percentage:
                            max_percentage = percentage
                            majority_class = class_code
                    
                    majority_classes.append(majority_class)
                    majority_percentages.append(max_percentage)
                    cover_stats_list.append(stats)
                    
                else:
                    print(f"   Unexpected statistics format: {type(stats)}")
                    majority_classes.append(None)
                    majority_percentages.append(None)
                    cover_stats_list.append(None)
                    
            except Exception as stats_error:
                print(f"   Error calculating cover statistics: {stats_error}")
                # Fallback: try alternative methods
                try:
                    if region in ['PR', 'HI']:
                        # Try RGB-aware fallback for PR and HI
                        fallback_stats = calculate_pr_rgb_statistics(cover_da)
                    else:
                        # For other regions, try standard cover_statistics as fallback
                        fallback_stats = nlcd.cover_statistics(cover_da)
                        print(f"   Used standard fallback analysis")
                        
                    # Handle different fallback result formats
                    if hasattr(fallback_stats, 'classes') and fallback_stats.classes:
                        # Standard pygeohydro statistics object
                        max_percentage = 0
                        majority_class = None
                        
                        for class_name, percentage in fallback_stats.classes.items():
                            if percentage > max_percentage:
                                max_percentage = percentage
                                majority_class = name_to_code.get(class_name, class_name)
                        
                        majority_classes.append(majority_class)
                        majority_percentages.append(max_percentage)
                        cover_stats_list.append(fallback_stats.classes)
                        
                    elif isinstance(fallback_stats, dict):
                        # Direct class statistics (from PR function)
                        majority_class = max(fallback_stats.keys(), key=lambda k: fallback_stats[k])
                        majority_percentage = fallback_stats[majority_class]
                        majority_classes.append(majority_class)
                        majority_percentages.append(majority_percentage)
                        cover_stats_list.append(fallback_stats)
                    else:
                        print(f"   Unexpected fallback statistics format: {type(fallback_stats)}")
                        majority_classes.append(None)
                        majority_percentages.append(None)
                        cover_stats_list.append(None)
                        
                except Exception as fallback_error:
                    print(f"   Fallback calculation also failed: {fallback_error}")
                    majority_classes.append(None)
                    majority_percentages.append(None)
                    cover_stats_list.append(None)
            
        except Exception as e:
            print(f"Error processing polygon {idx}: {str(e)}")
            majority_classes.append(None)
            majority_percentages.append(None)
            cover_stats_list.append(None)
    
    # Add results to the GeoDataFrame
    gdf['majority_nlcd_class'] = majority_classes
    gdf['majority_percentage'] = majority_percentages
    gdf['nlcd_cover_stats'] = cover_stats_list
    
    return gdf


def convert_nlcd_to_custom_codes(gdf: gpd.GeoDataFrame, region: str = 'L48') -> gpd.GeoDataFrame:
    """
    Convert NLCD class codes to USGS classification codes.
    
    Parameters:
    -----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame with NLCD results containing 'majority_nlcd_class' column
        
    Returns:
    --------
    gpd.GeoDataFrame
        GeoDataFrame with additional 'IVGTYP_nlcd' column
    """
    # NLCD to USGS code mapping
    nlcd_to_custom = {
        # Water bodies
        11: 16,  # Open water -> Water Bodies
        12: 24,  # Perennial ice / Snow
        
        # Developed/Urban land
        21: 6,  # Developed, open space -> Urban and Built-Up Land
        22: 6,  # Developed, low intensity -> Urban and Built-Up Land
        23: 1,   # Developed, med intensity -> Urban and Built-Up Land
        24: 1,   # Developed, high intensity -> Urban and Built-Up Land
        
        # Barren land
        31: 19,  # Barren land -> Barren or Sparsely Vegetated
        
        # Forest types
        41: 11,  # Deciduous forest -> Deciduous Broadleaf Forest
        42: 14,  # Evergreen forest -> Evergreen Needleleaf Forest
        43: 15,  # Mixed forest -> Mixed Forest
        
        # Shrubland
        51: 8,   # Dwarf shrub -> Shrubland
        52: 8,   # Shrub/scrub -> Shrubland
        
        # Grassland
        71: 9,   # Grassland/Herbaceous -> Mixed Shrubland/Grassland
        72: 20,  # Sedge -> Herbaceous Tundra
        73: 20,  # Lichens -> Herbaceous Tundra
        74: 20,  # Moss -> Herbaceous Tundra
        
        # Agricultural/Pasture
        81: 5,   # Pasture/Hay -> Dryland Cropland and Pasture
        82: 4,   # Cultivated crops -> Dryland Cropland and Pasture
        
        # Wetlands
        90: 18,  # Woody wetlands -> Wooded Wetland
        95: 17   # Herbaceous wetlands -> Herbaceous Wetland
    }
    
    # Create a copy to avoid modifying the original
    result_gdf = gdf.copy()
    
    # Apply the standard conversion for all regions
    result_gdf['IVGTYP_nlcd'] = result_gdf['majority_nlcd_class'].map(nlcd_to_custom)
    
    return result_gdf


def save_results_to_sql(gdf: gpd.GeoDataFrame, geopackage_path: str) -> None:
    """
    Save the NLCD results to the 'divide-attributes' table in the SQL database.
    
    Parameters:
    -----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame with NLCD results
    geopackage_path : str
        Path to the geopackage SQLite database
    """
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(geopackage_path)
        cursor = conn.cursor()
        
        # Check if the divide-attributes table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='divide-attributes';")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Create subset with required columns (excluding majority_nlcd_class and majority_percentage)
            gdf_subset = gdf[['divide_id', 'IVGTYP_nlcd']].copy()
            
            # Add new column to the table if it doesn't exist
            try:
                cursor.execute("ALTER TABLE `divide-attributes` ADD COLUMN IVGTYP_nlcd INTEGER;")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Update the table with new values
            updated_count = 0
            for _, row in gdf_subset.iterrows():
                update_query = """
                UPDATE `divide-attributes` 
                SET IVGTYP_nlcd = ? 
                WHERE `divide_id` = ?
                """
                
                cursor.execute(update_query, (
                    row['IVGTYP_nlcd'], 
                    row['divide_id']
                ))
                updated_count += 1
            
            conn.commit()
            print(f"Successfully updated {updated_count} records in 'divide-attributes' table")
            
        else:
            # Extract only the IVGTYP_nlcd column we want to save
            gdf_subset = gdf[['IVGTYP_nlcd']].copy()
            gdf_subset.to_sql('divide-attributes', conn, if_exists='replace', index=False)
            print(f"Created 'divide-attributes' table with {len(gdf_subset)} records")
        
        conn.close()
        
    except Exception as e:
        print(f"Error saving to SQL database: {str(e)}")
        print("Full error details:")
        import traceback
        print(traceback.format_exc())
        if 'conn' in locals():
            conn.close()


def process_folder_nlcd_analysis(
    folder_path: str,
    year: int = 2021,
    region: str = 'L48'
) -> None:
    """
    Process all .gpkg files in a folder for NLCD analysis.
    
    Parameters:
    -----------
    folder_path : str
        Path to the folder containing .gpkg files
    year : int, default 2021
        Year of NLCD data to use
    region : str, default 'L48'
        Region in the US
    """
    folder_path = Path(folder_path)
    
    # Find all .gpkg files recursively in the folder and subfolders
    gpkg_files = list(folder_path.rglob("*.gpkg"))
    
    if not gpkg_files:
        print(f"No .gpkg files found in {folder_path} or its subfolders")
        return
    
    print(f"Found {len(gpkg_files)} geopackage files to process")
    print("=" * 60)
    
    successful_files = []
    failed_files = []
    
    for i, gpkg_file in enumerate(gpkg_files, 1):
        start_time = time.time()
        
        try:
            print(f"\n[{i}/{len(gpkg_files)}] Processing: {gpkg_file.name}")
            print(f"    Path: {gpkg_file.parent}")
            
            # Run the analysis
            result_gdf = read_geopackage_and_calculate_nlcd_majority(
                geopackage_path=str(gpkg_file),
                year=year,
                region=region
            )
            
            # Convert NLCD codes to USGS codes
            result_gdf = convert_nlcd_to_custom_codes(result_gdf, region)
            
            # Save results to SQL database
            save_results_to_sql(result_gdf, str(gpkg_file))
            
            # Calculate processing time
            elapsed_time = time.time() - start_time
            
            # Summary for this file
            successful = result_gdf['majority_nlcd_class'].notna().sum()
            print(f"Completed: {successful}/{len(result_gdf)} polygons processed in {elapsed_time:.1f}s")
            
            successful_files.append(gpkg_file.name)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"Failed: {gpkg_file.name} - {str(e)} (after {elapsed_time:.1f}s)")
            failed_files.append(gpkg_file.name)
    
    # Final summary
    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total files processed: {len(gpkg_files)}")
    print(f"Successful: {len(successful_files)}")
    print(f"Failed: {len(failed_files)}")
    
    if successful_files:
        print(f"\nSuccessfully processed files:")
        for file in successful_files:
            print(f"  - {file}")
    
    if failed_files:
        print(f"\nFailed files:")
        for file in failed_files:
            print(f"  - {file}")


def main():
    """Main function to handle command line arguments and execute batch processing."""
    parser = argparse.ArgumentParser(
        description="Batch process geopackage files for NLCD land cover analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Data Availability by Region:
    L48 (CONUS):      Years 2001, 2004, 2006, 2008, 2011, 2013, 2016, 2019, 2021 available
    AK (Alaska):      Years 2001, 2011, 2016 available  
    HI (Hawaii):      Only 2001 available
    PR (Puerto Rico): Only 2001 available

Examples:
    # CONUS with recent data
    python nlcd_vegtyp.py /path/to/conus/folder --year 2021 --region L48
    
    # Puerto Rico (must use 2001)
    python nlcd_vegtyp.py /path/to/pr/folder --year 2001 --region PR
    
    # Alaska with available year
    python nlcd_vegtyp.py /path/to/alaska/folder --year 2016 --region AK
        """
    )
    
    parser.add_argument(
        'folder_path',
        help='Path to folder containing .gpkg files (searches subdirectories too)'
    )
    
    parser.add_argument(
        '--year',
        type=int,
        default=2021,
        choices=[2021, 2019, 2016, 2013, 2011, 2008, 2006, 2004, 2001],
        help='NLCD year to use (default: 2021). Note: not all years available for all regions - see examples.'
    )
    
    parser.add_argument(
        '--region',
        type=str,
        default='L48',
        choices=['L48', 'HI', 'AK', 'PR'],
        help='US region (default: L48 for CONUS). Different regions have different data availability.'
    )
    
    args = parser.parse_args()
    
    # Validate folder path
    if not os.path.exists(args.folder_path):
        print(f"Error: Folder '{args.folder_path}' does not exist")
        sys.exit(1)
    
    if not os.path.isdir(args.folder_path):
        print(f"Error: '{args.folder_path}' is not a directory")
        sys.exit(1)
    
    # Validate year/region combination before processing
    try:
        config = get_domain_nlcd_config(args.region, args.year)
        print(f"Configuration validated for {args.region} region, year {args.year}")
    except ValueError as e:
        print(f"Invalid configuration: {e}")
        print(f"\nAvailable years for {args.region}:")
        region_info = {
            'L48': [2001, 2004, 2006, 2008, 2011, 2013, 2016, 2019, 2021],
            'AK': [2001, 2011, 2016],
            'HI': [2001],
            'PR': [2001]
        }
        if args.region in region_info:
            available = ', '.join(map(str, region_info[args.region]))
            print(f"   {available}")
        sys.exit(1)
    
    # Run the batch processing
    print(f"Starting batch NLCD analysis...")
    print(f"Folder: {args.folder_path}")
    print(f"NLCD Year: {args.year}")
    print(f"Region: {args.region}")
    print()
    
    try:
        process_folder_nlcd_analysis(
            folder_path=args.folder_path,
            year=args.year,
            region=args.region
        )
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
