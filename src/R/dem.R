# @author Ahmad Jan Khattak
# @email ahmad.jan.khattak@noaa.gov
# @date  February 26, 2026


GetDEM <- function(div_infile,
                   dem_input_file,
                   buffer_m = 2000,
                   aggregate_factor = 3) {
  
  dem_corr_file <- glue("dem/dem_corr.tif")
  
  if (file.exists(dem_corr_file)) {
    message("dem/dem_corr.tif file exists, so skipping DEM processing...")
    return()
  }
  
  cat("=== Starting DEM processing ===\n")
  cat(glue("DEM input file1: {dem_input_file}\n"))
  
  terraOptions(tempdir = "/Volumes/BigDrive/terra_temp")
  
  # ----------------------------
  # Load DEM safely
  dem_output_dir <- "dem"
  
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
  cat(glue("\nDEM reprojected to EPSG:5070: {dem_proj_file}\n"))
  
  # ----------------------------
  # Breach depressions
  
  dem_corr_file <- file.path(dem_output_dir, "dem_corr.tif")
  wbt_breach_depressions(dem = dem_proj_file,
                         output = dem_corr_file)
  
  cat(glue("\nDepressions breached: {dem_corr_file}\n"))
  
  cat("=== DEM processing complete ===\n")
  
}