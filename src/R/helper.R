# @author Ahmad Jan Khattak
# @email ahmad.jan.khattak@noaa.gov
# @author Lauren Bolotin
# @email lauren.bolotin@noaa.gov
# @date  February 05, 2024


GetDEM <- function(div_infile,
                   dem_input_file,
                   dem_output_dir,
                   buffer_m = 2000,
                   aggregate_factor = 3) {

  cat("=== Starting DEM processing ===\n")
  cat(glue("DEM input file1: {dem_input_file}\n"))
  terraOptions(tempdir = "/Volumes/BigDrive/terra_temp")
  # ----------------------------
  # Load DEM safely
  
  tryCatch({
    elev <- rast(dem_input_file)
    cat("\nDEM loaded successfully.\n")
  }, error = function(e) {
    stop(glue("Failed to load DEM: {dem_input_file}\nDetails: {e$message}"))
  })

  # ----------------------------
  # Read the geopackage
  div      <- read_sf(div_infile, "divides")
  crs_div  <- st_crs(div)
  crs_elev <- crs(elev)
  
  if (!identical(crs_div, crs_elev)) {
    div <- st_transform(div, crs = crs_elev)
    cat("Reprojected divides to DEM CRS.\n")
  }

  # ----------------------------
  # Buffer divides (to avoid boundary issues)

  tryCatch({
    div_bf <<- st_buffer(div,dist=buffer_m)
  }, error = function(e) {
    cat ("Failed to create DEM buffer; cropping to divides instead\n")
  })

  cat(glue("Buffered divides by {buffer_m} meters.\n"))
  flush.console()

  # ----------------------------
  # Crop DEM to buffered divides

  tryCatch({
    dem <- crop(elev, vect(div_bf), snap = "out")
    cat("DEM cropped to buffered divides.\n")
  }, error = function(e) {
    warning("Buffer crop failed; cropping to divides only.")
    dem <- crop(elev, vect(div), snap = "out")
  })

  # ----------------------------
  # Convert units if VRT is in cm
  if (grepl("USGS_seamless_DEM_13.vrt", dem_input_file)) {
    dem <- dem * 0.01  # cm to m
    #dem <- as.float(dem)  # ensures FLT4S - note CONUS scale TWI/GIUHs etc. were produced using as.float(dem)
    cat("Converted DEM units from cm to m.\n")
  }

  # ----------------------------
  # Aggregate to coarser resolution

  if (aggregate_factor > 1) {
    cat(glue("Aggregating DEM by factor {aggregate_factor}...\n"))
    elev_file <- file.path(dem_output_dir, "dem_coarse.tif")

    dem <- aggregate(dem,
                     fact = aggregate_factor,
                     fun = "mean",
                     filename = elev_file,
                     overwrite = TRUE)
    cat("Aggregation complete.\n")
  }

  # ----------------------------
  # Remove negative values
  # ----------------------------

  dem[dem < 0] <- 0

  # ----------------------------
  # Write DEM to disk

  dem_file <- file.path(dem_output_dir, "dem.tif")
  writeRaster(dem, dem_file, datatype = "FLT4S", overwrite = TRUE)
  cat(glue("DEM written to {dem_file}\n"))
  
  # ----------------------------
  # Reproject DEM using gdalwarp

  dem_proj_file <- file.path(dem_output_dir, "dem_proj.tif")
  gdal_utils("warp",
             source = dem_file,
             destination = dem_proj_file,
             options = c("-of", "GTiff", "-t_srs", "EPSG:5070", "-r", "bilinear"))
  cat(glue("DEM reprojected to EPSG:5070: {dem_proj_file}\n"))
  
  # ----------------------------
  # Breach depressions

  dem_corr_file <- file.path(dem_output_dir, "dem_corr.tif")
  wbt_breach_depressions(dem = dem_proj_file,
                         output = dem_corr_file)
  cat(glue("Depressions breached: {dem_corr_file}\n"))
  
  cat("=== DEM processing complete ===\n")

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


  if (length(value) <= 0 || all(is.na(value)) || all(is.nan(value))) {
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
GetModelAttributes <- function(div_infile, hf_version = '2.1.1') {
  print ("ADD MODEL ATTRIBUTES FUNCTION")
  if (hf_version == "2.2") {
    print ("TODO: add divide attributes for HF v2.2.. stopping")
    stop()
  }
  else if (hf_version == "2.1.1"){
    base = 's3://lynker-spatial/hydrofabric/v2.1.1/nextgen/conus'    
  }

  # net has divide_id, id, and vupid that are used for filtering below
  #net = as_sqlite(div_infile, "network") 
  net = hfsubsetR::as_ogr(div_infile, "network")

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

  sf::st_write(model_attr, div_infile, layer = "model-attributes", append = FALSE)
  sf::st_write(flowpath_attr, div_infile, layer = "flowpath-attributes", append = FALSE)    
  

  return(model_attr)
  
  #### Method 2 - could be done this way too
  #net = as_sqlite(outfile, "network") |> 
  #  select('id', 'divide_id', 'vpuid') |> 
  #  collect()
  
  #model_attr <- open_dataset(glue('s3://lynker-spatial/hydrofabric/v{hf_version}/nextgen/conus_model-attributes')) |>
  #  filter(vpuid %in% unique(net$vpuid), divide_id %in% unique(net$divide_id)) |> 
  #  collect() 
  
  #flowpath_attr <- open_dataset(glue('s3://lynker-spatial/hydrofabric/v{hf_version}/nextgen/conus_flowpath-attributes')) |>
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

circular_mean <- function (values, coverage_fraction) {

  # adopted from the 'zonal' package: https://github.com/mikejohnson51/zonal/blob/8d932f3d419489f90e7ab6c6afa085791324dc46/R/custom_function.R#L30
  #TODO: figure out how to integrate the existing function
  degrad = pi / 180

  sinr <- sum(sin(values * degrad), na.rm = TRUE)

  cosr <- sum(cos(values * degrad), na.rm = TRUE)

  val = atan2(sinr, cosr) * (1 / degrad)

  ifelse(val < 0, 180 + (val + 180), val)

}
