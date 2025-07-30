# @author Seth Younger
# @email seth.younger@noaa.gov
# @date  July 17, 2025

# Function to calculate majority vegetation type from NLCD data on disk and convert to NWM codes
calc_maj_vegtyp_nlcd <- function(div_infile, nlcd_data_path) {

divides <- read_sf(div_infile, 'divides')

  # Read NLCD raster data
  nlcd <- rast(nlcd_data_path)

  # Create mapping from NLCD codes to NWM vegetation types
  nlcd_to_nwm_lookup <- c(
    # Water bodies
    "11" = "16",  # Open Water -> Water Bodies
    "12" = "24",  # Perennial Ice/Snow -> Snow or Ice
    
    # Developed/Urban land
    "21" = "6",   # Developed, Open Space -> Urban and Built-Up Land
    "22" = "6",   # Developed, Low Intensity -> Urban and Built-Up Land
    "23" = "1",   # Developed, Medium Intensity -> Urban and Built-Up Land
    "24" = "1",   # Developed, High Intensity -> Urban and Built-Up Land
    
    # Barren land
    "31" = "19",  # Barren Land (Rock/Sand/Clay) -> Barren or Sparsely Vegetated
    
    # Forest types
    "41" = "11",  # Deciduous Forest -> Deciduous Broadleaf Forest
    "42" = "14",  # Evergreen Forest -> Evergreen Needleleaf Forest
    "43" = "15",  # Mixed Forest -> Mixed Forest
    
    # Shrubland
    "51" = "8",   # Dwarf Scrub (Alaska) -> Shrubland
    "52" = "8",   # Shrub/Scrub -> Shrubland
    
    # Herbaceous/Grassland
    "71" = "7",   # Grassland/Herbaceous -> Grassland
    "72" = "20",  # Sedge/Herbaceous (Alaska) -> Herbaceous Tundra
    "73" = "20",  # Lichens (Alaska) -> Herbaceous Tundra
    "74" = "20",  # Moss (Alaska) -> Herbaceous Tundra
    
    # Planted/Cultivated
    "81" = "5",   # Pasture/Hay -> Cropland/Grassland Mosaic
    "82" = "2",   # Cultivated Crops -> Dryland Cropland and Pasture
    
    # Wetlands
    "90" = "18",  # Woody Wetlands -> Wooded Wetland
    "95" = "17"   # Emergent Herbaceous Wetlands -> Herbaceous Wetland
  )
  
  # Calculate majority landcover type for each divide
  divides$nlcd_maj <- exact_extract(nlcd, divides, fun = 'majority')
  
  # Convert NLCD codes to character and reclassify to NWM codes
  nlcd_codes_char <- as.character(divides$nlcd_maj)
  nwm_codes <- nlcd_to_nwm_lookup[nlcd_codes_char]
  
  # Convert back to numeric
  nwm_codes <- as.numeric(nwm_codes)
  
  # Report unmatched codes
  if (any(is.na(nwm_codes) & !is.na(divides$nlcd_maj))) {
    unmatched <- unique(divides$nlcd_maj[is.na(nwm_codes) & !is.na(divides$nlcd_maj)])
    message(paste("NLCD codes without NWM equivalents:", paste(unmatched, collapse = ", ")))
  }
  
  # Add the NWM vegetation type to the divides dataframe
  divides$IVGTYP_nlcd <- nwm_codes
  
  # Remove the temporary nlcd_maj column
  divides$nlcd_maj <- NULL

  return(divides)
}