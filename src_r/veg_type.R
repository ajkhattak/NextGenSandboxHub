# @author Seth Younger
# @email seth.younger@noaa.gov
# @date  July 17, 2025

# Function to calculate majority vegetation type from NLCD data and convert to NWM codes
calc_maj_vegtyp_nlcd <- function(div_infile, nlcd_data_path) {

divides <- read_sf(div_infile, 'divides')

  # Read NLCD raster data
  nlcd <- rast(nlcd_data_path)

  # Create mapping from NLCD codes to NWM vegetation types
  nlcd_to_nwm_lookup <- c(
    # Water bodies
    "11" = "16",  # Open water -> Water Bodies
    "12" = "24",  # Perennial ice / Snow
    
    # Developed/Urban land
    "21" = "81",   # Developed, open space -> Grassland or Herbaceous
    "22" = "81",   # Developed, low intensity -> Grassland or Herbaceous
    "23" = "1",   # Developed, med intensity -> Urban and Built-Up Land
    "24" = "1",   # Developed, high intensity -> Urban and Built-Up Land
    
    # Barren land
    "31" = "19",  # Barren land -> Barren or Sparsely Vegetated
    
    # Forest types
    "41" = "11",  # Deciduous forest -> Deciduous Broadleaf Forest
    "42" = "14",  # Evergreen forest -> Evergreen Needleleaf Forest
    "43" = "15",  # Mixed forest -> Mixed Forest
    # probably should have evergreen deciduous forests for PR?
    # 13: Evergreen Broadleaf Forest
    
    # Shrubland
    "51" = "8",   # Dwarf shrub (no direct NWM equivalent)
    "52" = "8",   # Shrub/scrub -> Shrubland
    
    # Grassland
    "71" = "9",   # Grassland/Herbaceous -> Mixed Shrubland/Grassland
    "72" = "20",  # Sedge -> Herbaceous Tundra
    "73" = "20",  # Lichens -> Herbaceous Tundra
    "74" = "20",  # Moss -> Herbaceous Tundra
    
    # Agricultural/Pasture
    "81" = "5",   # Pasture/Hay -> Dryland Cropland and Pasture
    "82" = "4",   # Cultivated crops -> Dryland Cropland and Pasture
    
    # Wetlands
    "90" = "18",  # Woody wetlands -> Wooded Wetland
    "95" = "17"   # Herbaceous wetlands -> Herbaceous Wetland
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