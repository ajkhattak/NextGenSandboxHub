# @author Lauren Bolotin
# @email lauren.bolotin@noaa.gov
# @date  July 16, 2025

# ########################### Slope ########################
# Function computes slope from a DEM to replace the hydrofabric slope values
slope_function <- function(div_infile, dem_output_dir) {
  
  div <- read_sf(div_infile, 'divides')
  
  # This was already run in twi_width.R
  # wbt_slope(dem = glue("{dem_output_dir}/dem_corr.tif"), output = glue("{dem_output_dir}/slope.tif"),
  #           verbose_mode = FALSE)
  slope <- rast(glue("{dem_output_dir}/slope.tif"))
  
  slope_cat <- zonal::execute_zonal(data = slope,
                                    geom = div,
                                    ID = "divide_id",
                                    fun = "mean")
  return(slope_cat)

  }
  


