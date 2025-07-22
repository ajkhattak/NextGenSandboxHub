# @author Seth Younger
# @email seth.younger@noaa.gov

#!/usr/bin/env python3
"""
Majority Vegetation type analysis from NLCD land cover data

This script reads hydrofabric geopackage files and uses HyRivers nlcd functionality to
calculate majority NLCD land cover vegetation type in USGS landcover codes.

Usage:
    python nlcd_vegtyp.py --help

    python nlcd_vegtyp.py /path/to/directory/with/gpkg/files

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

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

def read_geopackage_and_calculate_nlcd_majority(
    geopackage_path: str, 
    year: int = 2021,
    region: str = 'L48'
) -> gpd.GeoDataFrame:
    """
    Read a geopackage with multiple polygons and calculate the majority NLCD cover 
    (2021) for each polygon using HyRiver toolset.
    
    Parameters:
    -----------
    geopackage_path : str
        Path to the geopackage file (SQLite database)
    year : int, default 2021
        Year of NLCD data to use (2021, 2019, 2016, 2013, 2011, 2008, 2006, 2004, 2001)
    region : str, default 'L48'
        Region in the US ('L48' for CONUS, 'HI' for Hawaii, 'AK' for Alaska, 'PR' for Puerto Rico)
    
    Returns:
    --------
    geopandas.GeoDataFrame
        Original GeoDataFrame with additional columns for majority land cover class,
        percentage of majority class, and cover statistics
    """
    
    # Read the geopackage from SQL database
    print(f"Reading geopackage from SQL database: {geopackage_path}")
    gdf = gpd.read_file(geopackage_path)
    print(f"Loaded {len(gdf)} polygons from geopackage")
    print(f"CRS: {gdf.crs}")
    
    # Ensure the GeoDataFrame is in a geographic CRS (EPSG:4326) for HyRiver
    if gdf.crs != 'EPSG:4326':
        print("Converting CRS to EPSG:4326 for HyRiver compatibility...")
        gdf = gdf.to_crs('EPSG:4326')
    
    # Prepare years dictionary for NLCD data
    years = {'cover': [year]}
    
    # Get NLCD data for all polygons
    print(f"Fetching NLCD {year} data for all polygons...")
    nlcd_data = nlcd.nlcd_bygeom(
        geometry=gdf,
        resolution=30,  # 30m resolution (native NLCD resolution)
        years=years,
        region=region,
        crs=4326
    )
    
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
            
            # Find the majority class
            # stats.classes contains the percentages for each land cover class
            max_percentage = 0
            majority_class = None
            
            for class_name, percentage in stats.classes.items():
                if percentage > max_percentage:
                    max_percentage = percentage
                    majority_class = name_to_code.get(class_name, class_name)  # Convert to code
            
            majority_classes.append(majority_class)
            majority_percentages.append(max_percentage)
            cover_stats_list.append(stats.classes)
            
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


def convert_nlcd_to_custom_codes(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Convert NLCD class codes to custom classification codes.
    
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
    
    # Apply the conversion
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
            # Create subset with required columns (excluding majority_nlcd_class)
            gdf_subset = gdf[['divide_id', 'IVGTYP_nlcd', 'majority_percentage']].copy()
            
            # Add new columns to the table if they don't exist
            try:
                cursor.execute("ALTER TABLE `divide-attributes` ADD COLUMN IVGTYP_nlcd INTEGER;")
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute("ALTER TABLE `divide-attributes` ADD COLUMN majority_percentage REAL;")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Update the table with new values
            updated_count = 0
            for _, row in gdf_subset.iterrows():
                update_query = """
                UPDATE `divide-attributes` 
                SET IVGTYP_nlcd = ?, 
                    majority_percentage = ? 
                WHERE `divide_id` = ?
                """
                
                cursor.execute(update_query, (
                    row['IVGTYP_nlcd'], 
                    row['majority_percentage'], 
                    row['divide_id']
                ))
                updated_count += 1
            
            conn.commit()
            print(f"Successfully updated {updated_count} records in 'divide-attributes' table")
            
        else:
            # Extract only the columns we want to save (excluding majority_nlcd_class)
            gdf_subset = gdf[['IVGTYP_nlcd', 'majority_percentage']].copy()
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
            
            # Convert NLCD codes to custom codes
            result_gdf = convert_nlcd_to_custom_codes(result_gdf)
            
            # Save results to SQL database
            save_results_to_sql(result_gdf, str(gpkg_file))
            
            # Calculate processing time
            elapsed_time = time.time() - start_time
            
            # Summary for this file
            successful = result_gdf['majority_nlcd_class'].notna().sum()
            print(f"✓ Completed: {successful}/{len(result_gdf)} polygons processed in {elapsed_time:.1f}s")
            
            successful_files.append(gpkg_file.name)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"✗ Failed: {gpkg_file.name} - {str(e)} (after {elapsed_time:.1f}s)")
            failed_files.append(gpkg_file.name)
    
    # Final summary
    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total files processed: {len(gpkg_files)}")
    print(f"Successful: {len(successful_files)}")
    print(f"Failed: {len(failed_files)}")
    
    if successful_files:
        print(f"\n✓ Successfully processed files:")
        for file in successful_files:
            print(f"  - {file}")
    
    if failed_files:
        print(f"\n✗ Failed files:")
        for file in failed_files:
            print(f"  - {file}")


def main():
    """Main function to handle command line arguments and execute batch processing."""
    parser = argparse.ArgumentParser(
        description="Batch process geopackage files for NLCD land cover analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python batch_nlcd_analysis.py /path/to/geopackage/folder
    python batch_nlcd_analysis.py /path/to/folder --year 2019 --region L48
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
        help='NLCD year to use (default: 2021)'
    )
    
    parser.add_argument(
        '--region',
        type=str,
        default='L48',
        choices=['L48', 'HI', 'AK', 'PR'],
        help='US region (default: L48 for CONUS)'
    )
    
    args = parser.parse_args()
    
    # Validate folder path
    if not os.path.exists(args.folder_path):
        print(f"Error: Folder '{args.folder_path}' does not exist")
        sys.exit(1)
    
    if not os.path.isdir(args.folder_path):
        print(f"Error: '{args.folder_path}' is not a directory")
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
