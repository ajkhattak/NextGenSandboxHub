# @author Seth Younger
# @email seth.younger@noaa.gov
# @date  July 17, 2025
# Modified by Ahmad Jan Khattak (1/28/2026)

# Calculate vegetation type(s) from NLCD and convert the veg type ID to Noah-MP (USGS) look table.
# Supports either majority/mode class or fractional dominant N vegetation types.

# Function to calculate majority vegetation type from NLCD data on disk and convert to NWM codes
ComputeVegTypeNLCD <- function(div_infile, 
                               nlcd_data_path,
                               veg_method = c("majority", "fraction"),
                               nclasses = 2
                               ) {
  
  veg_method <- match.arg(veg_method)
  
  # Read divides & NLCD raster data
  div  <- read_sf(div_infile, 'divides')
  nlcd <- rast(nlcd_data_path)

  # Create mapping from NLCD codes to NWM vegetation types
  nlcd_to_nwm_lookup <- c(
    # Water bodies
    "11" = "16",  # Open Water -> Water Bodies
    "12" = "24",  # Perennial Ice/Snow -> Snow or Ice
    
    # Developed/Urban land
    "21" = "1",   # Developed, Open Space -> Urban and Built-Up Land
    "22" = "1",   # Developed, Low Intensity -> Urban and Built-Up Land
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
  
  nlcd_frac <- exact_extract(nlcd, div, fun = "frac")
  
  # Aggregate to USGS/NWM veg types
  veg_agg <- apply(nlcd_frac, 1, aggregate_nlcd_to_nwm,
                   nlcd_to_nwm_lookup = nlcd_to_nwm_lookup
                   )
  
  # ----- MAJORITY METHOD -----
  if (veg_method == "majority") {
    
    div$IVGTYP_nlcd <- sapply(veg_agg, function(df) {
      if (is.null(df) || nrow(df) == 0) {
        return(NA_real_)
      }
      df$nwm[which.max(df$fraction)]
    })
  }

  if (veg_method == "fraction") {
    
    div$IVGTYP_nlcd <- sapply(veg_agg, function(df) {

      if (is.null(df) || nrow(df) == 0) {
        return(NA_character_)
        }
        
        # Ensure sorted
        df <- df[order(-df$fraction), ]
        df <- head(df, nclasses)
        
        # Normalize
        df$fraction <- df$fraction / sum(df$fraction)
        
        # Rename columns to desired schema (consistent with other divide-attributes)
        out <- data.frame(v = df$nwm, frequency = round(df$fraction, 4))
        
        # Convert to JSON (no pretty-printing)
        toJSON(out, auto_unbox = TRUE)
      })

  }

  return(div)
}


aggregate_nlcd_to_nwm <- function(row, nlcd_to_nwm_lookup) {
  
  df <- tibble(
    nlcd = sub("frac_", "", names(row)),
    fraction = as.numeric(row)
  )
  
  df <- df[df$fraction > 0, ]
  
  df$nwm <- as.numeric(nlcd_to_nwm_lookup[df$nlcd])
  df <- df[!is.na(df$nwm), ]
  
  if (nrow(df) == 0) return(NULL)
  
  df %>%
    group_by(nwm) %>%
    summarise(fraction = sum(fraction), .groups = "drop") %>%
    arrange(desc(fraction))
}

#Majority is now computed in NWM space after NLCD→NWM aggregation, using the same fractional machinery as the fraction method.
# Dominance must be computed after categorical aggregation, never before.
