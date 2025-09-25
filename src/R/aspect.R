# @author Lauren Bolotin
# @email lauren.bolotin@noaa.gov
# @date  Aug 25, 2025

# ########################### Slope ########################
# Function computes aspect from a DEM to replace the hydrofabric aspect values

aspect_function <- function(div_infile, dem_output_dir) {
  div <- read_sf(div_infile, 'divides')

  dem <- rast(glue("{dem_output_dir}/dem_corr.tif"))
  aspect <- wbt_aspect(dem, glue("{dem_output_dir}/aspect.tif"))
  aspect <- rast(glue("{dem_output_dir}/aspect.tif"))

  aspect_cat <- zonal::execute_zonal(data = aspect,
                                    geom = div,
                                    ID = "divide_id",
                                    fun = circular_mean)
  
  return(aspect_cat)
  
}



