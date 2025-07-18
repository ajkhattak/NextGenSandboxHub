# @author Ahmad Jan Khattak
# @email ahmad.jan.khattak@noaa.gov
# @author Lauren Bolotin
# @email lauren.bolotin@noaa.gov
# @date  February 05, 2024

# Get the DEM
dem_function <- function(div_infile,
                         dem_input_file = NULL,
                         dem_output_dir) {
  print ("DEM FUNCTION")
  print (glue("DEM file: ", dem_input_file))
  
  tryCatch({
    elev <- rast(dem_input_file)
  }, error = function(e) {
    cat ("Error: dem_input_file does not exist: provided ", dem_input_file, "\n")
    cat("Details:", e$message, "\n")
  })
  
  # Get the catchment geopackage
  div <- read_sf(div_infile, 'divides')
  crs_div <- st_crs(div)
  crs_elev <- crs(elev)
  
  if (!identical(crs_div, crs_elev)) {
    div <- st_transform(div, crs = crs_elev)
  }
  
  # Buffer because we want to guarantee we don not have boundary issues when processing the DEM
  tryCatch({
    div_bf <<- st_buffer(div,dist=5000) # didn't use this for the one AK basin
    dem <<- crop(elev, project(vect(div_bf), crs(elev)), snap = "out") 
  }, error = function(e) {
    cat ("Failed to create DEM buffer; cropping to divides instead\n")
    dem <<- crop(elev, project(vect(div), crs(elev)), snap = "out") # cropped the one AK basin to div, not div_bf
    cat ("Successfully cropped DEM to divides\n")
  })

  if (grepl("dem.vrt", dem_input_file)) { # If using the original DEM, need to convert units
    cm_to_m <- 0.01
    dem <- dem * cm_to_m
  } # If using USGS 10 m DEM, do not need to convert units

  # Checking for NaN values
  if (any(is.nan(values(dem)))) {
    print (glue("Warning: The DEM contains NaN values."))
  }
  
  dem[dem < 0] <- 0      # Convert negative values to NA
  
  if (grepl("USGS_seamless_13.vrt", dem_input_file)) { # If using USGS 10 m DEM, need to aggregate
    dem <- raster(dem)
    dem <- aggregate(dem, fact = 3, fun = mean)
  }
  
  writeRaster(dem, glue("{dem_output_dir}/dem.tif"), overwrite = TRUE)
  
  gdal_utils("warp",
             source = glue("{dem_output_dir}/dem.tif"),
             destination = glue("{dem_output_dir}/dem_proj.tif"),
             options = c("-of", "GTiff", "-t_srs", "EPSG:5070", "-r", "bilinear")
  )
  
  wbt_breach_depressions(dem = glue("{dem_output_dir}/dem_proj.tif"), 
                         output = glue("{dem_output_dir}/dem_corr.tif") )
  
}


#the condition [coverage_fraction > .1] excludes/drops all cell X that has fraction less than 10% in the divide Y
fun_crop_lower <- function(values, coverage_fraction) {
  data = (values * coverage_fraction)[coverage_fraction > 0.1]
  percentile_10 <- unname(quantile(data, probs = 0.15, na.rm = TRUE)) # unname function returns the quantile value only, and not the cut points
  data[data <= percentile_10] = percentile_10
}

fun_crop_upper <- function(values, coverage_fraction) {
  data = (values * coverage_fraction)[coverage_fraction > .1]
  percentile_90 <- unname(quantile(data, probs = 0.85, na.rm = TRUE))
  data[data >= percentile_90] = percentile_90
}

# Adapted from the distribution function at: https://github.com/mikejohnson51/zonal/blob/master/R/custom_function.R
corrected_distrib_func = function(value, coverage_fraction, breaks = 10, constrain = FALSE){
  
  if (length(value) <= 0 | all(is.nan(value))) {
    return("[]")
  }
  
  x1 = value*coverage_fraction
  x1 = x1[!is.na(x1)]
  
  if(constrain & length(breaks) > 1){
    
    breaks_tmp = c(breaks[1],breaks[2])
    
    ulimit = max(x1, na.rm = TRUE)
    
    if (ulimit < max(breaks, na.rm = TRUE)){
      ulimit = min(breaks[breaks >= ulimit])
    }
    
    breaks = breaks[breaks <= ulimit]
    
    if (length(breaks) == 1){
      breaks = breaks_tmp
    }
    
  }
  
  tmp = as.data.frame(table(cut(x1, breaks = breaks)))
  
  tmp$v = as.numeric(gsub("]", "", sub('.*,\\s*', '', tmp$Var1)))
  
  len <- length(tmp$Freq)
  len2 <- len - 1
  
  if (sum(tmp$Freq) == 0){
    tmp$Freq[1:len2] <- 0
    tmp$Freq[len] <- 1
  }  
  tmp$frequency = tmp$Freq / sum(tmp$Freq)
  
  
  if (sum(tmp$frequency) > 1.01 | sum(tmp$frequency) < 0.99){
    stop("No data in the distribution")
  }
  
  as.character(toJSON(tmp[,c("v", "frequency")]))
  
  
}




# Add model attribtes to the geopackage
add_model_attributes <- function(div_infile, hf_version = 'v2.1.1', write_attr_parquet = FALSE) {
  print ("ADD MODEL ATTRIBUTES FUNCTION")
  
  base = 's3://lynker-spatial/hydrofabric/v2.1.1/nextgen/conus'

  # net has divide_id, id, and vupid that are used for filtering below
  net = as_sqlite(div_infile, "network") 

  # Courtesy of Mike Johnson
  print ("Extracting model-attributes from .parquet file on S3 bucket")
  model_attr <- arrow::open_dataset(glue('{base}_model-attributes')) |>
    dplyr::inner_join(dplyr::collect(dplyr::distinct(dplyr::select(net, divide_id, vpuid)))) |> 
    dplyr::collect() 

  print ("Extracting flowpath-attributes from .parquet file on S3 bucket")
  flowpath_attr <- arrow::open_dataset(glue('{base}_flowpath-attributes')) |>
    dplyr::inner_join(dplyr::collect(dplyr::distinct(dplyr::select(net, id, vpuid)))) |> 
    dplyr::collect()

  #cat ("m_attr: ", nrow(model_attr))
  stopifnot(nrow(model_attr) > 0)
  stopifnot(nrow(flowpath_attr) > 0)
  
  # Write the attributes to a new table in the hydrofabric subset GPKG
  if (!write_attr_parquet) {
    sf::st_write(model_attr, div_infile, layer = "model-attributes", append = FALSE)
    sf::st_write(flowpath_attr, div_infile, layer = "flowpath-attributes", append = FALSE)    
  }
  else {
    #var = strsplit(div_infile, "\\.")[[1]][1]
    var = glue("{getwd()}/data")
    attr_par_dir = glue("{var}/flowpath-attributes.parquet")
    arrow::write_parquet(flowpath_attr,attr_par_dir)
  }

  
  return(model_attr)
  
  #### Method 2 - could be done this way too
  #net = as_sqlite(outfile, "network") |> 
  #  select('id', 'divide_id', 'vpuid') |> 
  #  collect()
  
  #model_attr <- open_dataset(glue('s3://lynker-spatial/hydrofabric/{hf_version}/nextgen/conus_model-attributes')) |>
  #  filter(vpuid %in% unique(net$vpuid), divide_id %in% unique(net$divide_id)) |> 
  #  collect() 
  
  #flowpath_attr <- open_dataset(glue('s3://lynker-spatial/hydrofabric/{hf_version}/nextgen/conus_flowpath-attributes')) |>
  #  filter(vpuid %in% unique(net$vpuid), divide_id %in% unique(net$id)) |> 
  #  collect()
}

# get parameter function check if a param is provided otherwise a default value
get_param <- function(input, param, default_value) {

  tryCatch({
    value = eval(parse(text = paste("input$", param, sep = "")))
    
    if (is.null(value)) default_value else value
    }, error = function(e) {
      default_value
    })
}

reprojection_function <- function(outfile, epsg = 5070){
  # File paths
  gpkg_path <- outfile
  gpkg_temp <- tempfile(fileext = ".gpkg")
  # Get all layer names
  sf_layers <- st_layers(gpkg_path)
  
  # Track first write
  first <- TRUE
  
  for (layer in sf_layers$name) {
    # Read layer
    layer_data <- st_read(gpkg_path, layer = layer, quiet = TRUE)
    # Reproject only if it's an sf object
    if (inherits(layer_data, "sf")) {
      layer_data <- st_transform(layer_data, crs = 5070)
    }
    # Write to new GPKG
    st_write(
      layer_data,
      gpkg_temp,
      layer = layer,
      delete_dsn = first,
      append = !first,
      quiet = TRUE
    )
    first <- FALSE
  }
  
  # Replace original GPKG
  # file_delete(gpkg_path)
  # file_copy(gpkg_temp, gpkg_path)
  file.remove(gpkg_path)
  file.copy(gpkg_temp, gpkg_path, overwrite = TRUE)
}
