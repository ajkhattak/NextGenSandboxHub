#----------------------- DOWNLOAD GEOPACKAGE ----------------------------------#
# STEP #3: provide USGS gauge id or your own geopackage (single or multiple)
#------------------------------------------------------------------------------#


############################ DRIVER_GIVEN_GAGE_ID ##############################
# main script that loops over all the gage IDs and computes giuh/twi etc.
DriverGivenGageIDs <- function(gage_ids, 
                               output_dir,
                               dem_input_file = NULL,
                               dem_output_dir = "",
                               compute_divide_attributes = FALSE,
                               nlcd_data_path = "",
                               calculate_vegetation = FALSE,
                               dem_aggregate_factor = 3,
                               veg_method = NULL
                               ) 
  {
  
  print ("DRIVER GIVEN GAGE ID")

  dir.create(glue("{output_dir}/basins_failed"), recursive = TRUE, showWarnings = FALSE)

  lapply(X = gage_ids, FUN = ProcessCatchmentID)

  setwd(output_dir)

}

#-----------------------------------------------------------------------------#
# Function called by pblapply for parallel processing by each worker/node
# for each catchemnt id
# it calls run_driver for each gage id and computes giuh/twi etc.

ProcessCatchmentID <- function(id) {

  print ("PROCESS CATCHMENT ID FUNCTION")

  cat_dir = glue("{output_dir}/{id}")
  dir.create(cat_dir, recursive = TRUE, showWarnings = FALSE)

  setwd(cat_dir)
  wbt_wd(getwd())

  # DEM and related files (such as projected/corrected DEMs, and specific contributing area rasters are stored here)
  dem_dir = "dem"
  dir.create(dem_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create("data", recursive = TRUE, showWarnings = FALSE)

  failed <- TRUE

  tryCatch({
    cat ("Processing catchment: ", id, "\n")
    RunDriver(gage_id = id,
              dem_input_file = dem_input_file,
              dem_output_dir = dem_dir,
              compute_divide_attributes = compute_divide_attributes,
              dem_aggregate_factor = dem_aggregate_factor,
              veg_method = veg_method
              )

    failed <- FALSE
  }, error = function(e) {
    failed <- TRUE
  })

  # move (or delete) dem output directory out of the main output directory

  clean_move_dem_dir(id = id, output_dir = output_dir, dem_output_dir = dem_output_dir)

  if (failed) {
    cat ("Basin failed:", id, "\n")
    cat_failed_dir = glue("{output_dir}/basins_failed/{id}")

    if (file.exists(cat_failed_dir) ) {
      unlink(cat_failed_dir, recursive = TRUE)
    }

    file.rename(cat_dir, cat_failed_dir)

  }
  else {
    cat ("Basin Passed:", id, "\n")
  }

}

############################ DRIVER_GIVEN_GPKG #################################
# main script that loops over all the geopackages and computes giuh/twi etc.
DriverGivenGPKG <- function(gage_files, 
                            gpkg_dir, 
                            output_dir,
                            dem_output_dir = "",
                            dem_input_file = NULL,
                            compute_divide_attributes = FALSE,
                            nlcd_data_path = "",
                            calculate_vegetation = FALSE,
                            dem_aggregate_factor = 3,
                            veg_method = NULL
                            ) 
  {

  print ("DRIVER GIVEN GEOPACKAGE FUNCTION")

  stopifnot(length(gage_files) >= 1)

  failed_dir <- glue("{output_dir}/basins_failed")

  if (dir.exists(failed_dir)) {
    unlink(failed_dir, recursive = TRUE)
  }
  dir.create(failed_dir, recursive = TRUE, showWarnings = FALSE)

  cats_failed <- lapply(X = gage_files, FUN = ProcessGPKG, failed_dir)
  setwd(output_dir)

  return(cats_failed)
}

ProcessGPKG <- function(gfile, failed_dir) {

  print ("PROCESS GPKG FUNCTION")

  # vector containing IDs of failed (for some reason) basins
  cats_failed <- numeric(0)

  id <- sub(".*_(.*?)\\..*", "\\1", basename(gfile))

  if (is.na(id)) {
     id <- 11111111
  }

  cat_dir = glue("{output_dir}/{id}")
  dir.create(cat_dir, recursive = TRUE, showWarnings = FALSE)

  setwd(cat_dir)
  wbt_wd(getwd())

  # DEM and related files (such as projected/corrected DEMs, and specific contributing 
  # area rasters are stored here)
  dem_dir = "dem"
  dir.create(dem_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create("data", recursive = TRUE, showWarnings = FALSE)
  file.copy(gfile, "data")

  failed <- TRUE

  tryCatch({
    cat ("Processing catchment: ", id, "\n")

    gpkg_name = basename(gfile)

    local_gpkg_file = glue("{cat_dir}/data/{gpkg_name}")

    RunDriver(is_gpkg_provided = TRUE,
              loc_gpkg_file = local_gpkg_file,
              dem_output_dir = dem_dir,
              dem_input_file = dem_input_file,
              compute_divide_attributes = compute_divide_attributes,
              dem_aggregate_factor = dem_aggregate_factor,
              veg_method = veg_method
              )

    failed <- FALSE

    }, error = function(e) {
      failed <- TRUE
    })

  # move (or delete) dem output directory out of the main output directory
  clean_move_dem_dir(id = id, output_dir = output_dir, dem_output_dir = dem_output_dir)

  if (failed) {
    cat ("Basin failed:", id, "\n")
    cat_failed_dir = glue("{output_dir}/basins_failed/{id}")

    if (file.exists(cat_failed_dir) ) {
      unlink(cat_failed_dir, recursive = TRUE)
    }

    file.rename(cat_dir, cat_failed_dir)

  }
  else {
    cat ("Basin Passed:", id, "\n")
  }
  
  return(cats_failed)

}

############################# RUN_DRIVER ######################################
# main runner function
RunDriver <- function(gage_id = NULL, 
                      is_gpkg_provided = FALSE, 
                      dem_input_file = NULL,
                      dem_output_dir,
                      loc_gpkg_file = "",
                      compute_divide_attributes = FALSE,
                      twi_pre_computed_option = FALSE,
                      dem_aggregate_factor = 3,
                      veg_method = NULL
                      ) {

  print ("RUN DRIVER FUNCTION")

  outfile <- " "
  if(!is_gpkg_provided) {
    start.time <- Sys.time()
    outfile <- glue('data/gage_{gage_id}.gpkg')

    # Get domain info for this gage
    gage_metadata <- suppressMessages(readNWISsite(gage_id)) |> 
      dplyr::select(state_cd)

    state_code <- gage_metadata$state_cd
    state <- stateCd$STUSAB[which(stateCd$STATE == state_code)]
      if (state %in% c("HI", "AK")) {
        domain <- tolower(state)
      } else if (state %in% c("PR", "VI")) {
        domain <- "prvi"
      } else {
        domain <- "conus"
      }

      # If the gpkg exists, use that for subsetting
      if (hf_version == "2.2") {

        if (file.exists(hf_gpkg_path)) {
          print('USING LOCAL GPKG FILE FOR SUBSETTING')
          hf_gpkg <- hf_gpkg_path
        } else {
          print('USING REMOTE GPKG FILE FOR SUBSETTING')
          hf_gpkg = NULL
        }

        layers = c("divides", "flowpaths", "network", "nexus",
                   "flowpath-attributes","divide-attributes")

        if (compute_divide_attributes) {
            layers = c("divides", "flowpaths", "network", "nexus")
        }
        if (domain != "conus"){ # If the gage is in oCONUS, query using flowpath id
          flowpath_id <- sf::read_sf(hf_gpkg, query = glue::glue(
            "SELECT hf_id FROM hydrolocations WHERE hl_reference || '-' || hl_link = 'Gages-{gage_id}'"
          ))$hf_id
          hfsubsetR::get_subset(comid = flowpath_id,
                                outfile = outfile,
                                gpkg = hf_gpkg,
                                hf_version = hf_version,
                                lyrs = layers,
                                type = 'nextgen',
                                overwrite = TRUE)
        } else{ # If the gage is in CONUS, query using hl_uri
          hfsubsetR::get_subset(hl_uri = glue("gages-{gage_id}"),
                                outfile = outfile,
                                gpkg = hf_gpkg,
                                hf_version = hf_version,
                                lyrs = layers,
                                type = 'nextgen',
                                overwrite = TRUE)
        }
      } else if (hf_version == "2.1.1") {
        layers = c("divides", "flowlines", "network", "nexus",
                   "flowpath-attributes","model-attributes")
        
        if (compute_divide_attributes) {
          layers = c("divides", "flowlines", "network", "nexus")
        }

        hfsubsetR::get_subset(nldi_feature = list(featureSource="nwissite", featureID=glue("USGS-{gage_id}")),
                              outfile = outfile, 
                              hf_version = hf_version, 
                              domain = "conus",
                              lyrs = layers,
                              overwrite = TRUE)
      }
    time.taken <- as.numeric(Sys.time() - start.time, units = "secs") #end.time - start.time
    print (paste0("Time (geopackage) = ", time.taken))

  } else { 
    outfile <- loc_gpkg_file
  }

  # check if the divide-attributes layer has the same number of rows as the divides layer
  if (!compute_divide_attributes) {
    check_divs  <- st_read(outfile, layer = 'divides')
    check_attrs <- st_read(outfile, layer = 'divide-attributes')

    id_col <- "divide_id"

    missing_in_attrs <- setdiff(check_divs[[id_col]], check_attrs[[id_col]])

    missing_in_divs <- setdiff(check_attrs[[id_col]], check_divs[[id_col]])

    if (length(missing_in_attrs) > 0 || length(missing_in_divs) > 0) {
      print("Mismatched rows detected:")
      print(glue("DIVIDES HAS {nrow(check_divs)} ROWS BUT DIVIDE-ATTRIBUTES HAS {nrow(check_attrs)}!!"))

      print(glue("IDs in divides but not in divide-attributes: {toString(missing_in_attrs)}"))
      print(glue("IDs in divide-attributes but not in divides: {toString(missing_in_divs)}"))
      stop()
    }

  }
 
  ## Stop if .gpkg does not exist

  if (!file.exists(outfile)) {
    print(glue("FILE '{outfile}' DOES NOT EXIST!!"))
    stop()
    }


  ########################## MODELS' ATTRIBUTES ##################################
  # STEP #4: Add models' attributes
  ########################## MODELS' ATTRIBUTES ##################################
  # STEP #4: Add models' attributes from the parquet file to the geopackage
  # this TRUE will be changed once synchronized HF bugs are fixed

  if(compute_divide_attributes) {
     #print layers before appending model attributes
     layers_before_cfe_attr <- sf::st_layers(outfile)
     print (layers_before_cfe_attr$name)
     start.time <- Sys.time()

     d_attr <- GetModelAttributes(div_infile = outfile, hf_version = hf_version)

     time.taken <- as.numeric(Sys.time() - start.time, units = "secs") #end.time - start.time
     print (paste0("Time (model attrs) = ", time.taken))
   } else {
     d_attr <- read_sf(outfile, 'divide-attributes')
   }


  ############################### GENERATE TWI ##################################
  # STEP #5: Generate TWI and width function and write to the geopackage
  # Note: The default distribution = 'quantiles'

  start.time <- Sys.time()
  dem_corr_file <- glue("{dem_output_dir}/dem_corr.tif")

  if (file.exists(dem_corr_file)) {
    message("dem/dem_corr.tif file exists, so skipping this step..")
  } else {
    message("DEM correction file does not exist.")
    GetDEM(div_infile = outfile, dem_input_file, dem_output_dir,
           buffer_m = 2000, aggregate_factor = dem_aggregate_factor)
  }


  time.taken <- as.numeric(Sys.time() - start.time, units = "secs") #end.time - start.time
  print (paste0("Time (dem func) = ", time.taken))

  print("STEP: Computing TWI and Width function .................")
  start.time <- Sys.time()
  twi <- ComputeTWI(div_infile = outfile, dem_output_dir = dem_output_dir,
                    distribution = 'simple', nclasses = 30)

  width_dist <- ComputeWidth(div_infile = outfile, dem_output_dir = dem_output_dir)

  twi_dat_values = data.frame(ID = twi$divide_id, twi = twi$fun.twi,
                              width_dist = width_dist$fun.downslope_fp_length)

  # write TWI and width function layers to the geopackage
  names(twi_dat_values)
  colnames(twi_dat_values) <- c('divide_id', 'twi', 'width_dist')
  names(twi_dat_values)


  ### NOTES: Pre-computed TWI
  # Note 1: model attributes layer ships with pre-computed TWI distribution with four equal quantiles
  #d_attr$twi_dist_4

  # Note 2: The user can also compute their own distribution from the pre-computed TWI using the dataset
  # available at s3://lynker-spatial/gridded-resources/twi.vrt

  if (twi_pre_computed_option) {
    twi_pre_computed <- twi_pre_computed_function(div_infile = outfile, distribution = 'simple',
                                                  nclasses = 30)
  }

  time.taken <- as.numeric(Sys.time() - start.time, units = "secs")
  print (paste0("Time (twi func) = ", time.taken))

  ############################### GENERATE GIUH ################################
  # STEP #6: Generate GIUH and write to the geopackage
  # There are many "model" options to specify the velocity.
  # Here we are using a simple approach: constant velocity as a function of upstream drainage area.
  print("STEP: Computing GIUH.................")
  start.time <- Sys.time()
  vel_channel     <- 1.0  # meter/second
  vel_overland    <- 0.1  # Fred: 0.1
  vel_gully       <- 0.2 # meter per second
  gully_threshold <- 30.0 # m (longest , closer to 10-30 m, Refs) 

  giuh_compute <- ComputeGIUH(div_infile = outfile, dem_output_dir = dem_output_dir, 
                              vel_channel, vel_overland, vel_gully, gully_threshold)

  #giuh_compute[2,] %>% t()
  
  # write GIUH layer to the geopackage
  giuh_dat_values = data.frame(ID = giuh_compute$divide_id, giuh = giuh_compute$fun.giuh_minute)
  colnames(giuh_dat_values) <- c('divide_id', 'giuh')

  time.taken <- as.numeric(Sys.time() - start.time, units = "secs")
  print (paste0("Time (giuh ftn) = ", time.taken))

  #######################. COMPUTE NASH CASCADE PARAMS ###########################
  # STEP #7: Generate Nash cascade parameters for surface runoff

  print("STEP: Computing Nash Cascade parameters .............")
  start.time <- Sys.time()
  nash_params_surface <- GetNashParams(giuh_dat_values, calib_n_k = FALSE)

  time.taken <- as.numeric(Sys.time() - start.time, units = "secs") #end.time - start.time
  print (paste0("Time (nash func) = ", time.taken))

  ####################### CALCULATE VEGETATION TYPE ############################
  # STEP #8a: Calculate vegetation type from NLCD data if enabled
  divides_with_veg <- NULL
  if (calculate_vegetation && nlcd_data_path != "" && file.exists(nlcd_data_path)) {
    print("STEP: Computing vegetation type from NLCD data .................")
    start.time <- Sys.time()

    # Calculate vegetation type
    divides_with_veg <- ComputeVegTypeNLCD(outfile, nlcd_data_path, veg_method, nclasses = 2)

    time.taken <- as.numeric(Sys.time() - start.time, units = "secs")
    print (paste0("Time (vegetation calc) = ", time.taken))
  } else if (calculate_vegetation) {
    print("WARNING: Vegetation calculation requested but NLCD data path not provided or file does not exist")
  }

  #######################. COMPUTE TERRAIN SLOPE ###########################
  # STEP #8: Take slope from the slope grid calculated in the TWI function
  slope <-  slope_function(div_infile = outfile, dem_output_dir = dem_output_dir)

  #######################. COMPUTE ASPECT ###########################
  # STEP #8b: Compute aspect from the DEM 
  aspect <-  aspect_function(div_infile = outfile, dem_output_dir = dem_output_dir)
  ####################### WRITE MODEL ATTRIBUTE FILE ###########################
  # STEP #9: Append GIUH, TWI, width function, slope, and Nash cascade N and K parameters
  # to model attributes layers

  d_attr$giuh <- giuh_dat_values$giuh             # append GIUH column to the model attributes layer

  d_attr$twi  <- twi_dat_values$twi               # append TWI column to the model attributes layer

  d_attr$width_dist <- twi_dat_values$width_dist  # append width distribution column to the model attributes layer

  d_attr$N_nash_surface <- nash_params_surface$N_nash

  d_attr$K_nash_surface <- nash_params_surface$K_nash
  d_attr$terrain_slope <- slope$mean.slope
  d_attr$terrain_aspect <- aspect$fun.aspect

  # Fix attribute naming issues (specific to PR hydrofabric)
  if ("mode.bexp_Time=_soil_layers_stag=1" %in% names(d_attr)) {
    d_attr <- dplyr::rename(d_attr, `mode.bexp_soil_layers_stag.1` = `mode.bexp_Time=_soil_layers_stag=1`)
  }

  if ("mean.refkdt_Time=" %in% names(d_attr)) {
    d_attr <- dplyr::rename(d_attr, `mean.refkdt` = `mean.refkdt_Time=`)
  }

  # Add vegetation type if calculated
  if (!is.null(divides_with_veg)) {
    d_attr$IVGTYP_nlcd <- divides_with_veg$IVGTYP_nlcd
  }

  if (hf_version == "2.2") {
    sf::st_write(d_attr, outfile,layer = "divide-attributes", append = FALSE, overwrite = TRUE)
  } else if (hf_version == "2.1.1") {
    sf::st_write(d_attr, outfile,layer = "model-attributes", append = FALSE)  
  }
  # Reproject to ensure all .gpkgs end up in Albers projection (EPSG:5070)
  reprojection_function(outfile)
}

clean_move_dem_dir <- function(id = id,
                               output_dir = output_dir,
                               dem_output_dir = dem_output_dir) {

  dem_target <- glue("{dem_output_dir}/{id}")
  dem_source <- glue("{output_dir}/{id}/dem")

  if (is.null(dem_output_dir) || dem_output_dir == "") {

    message("DEM output directory is set to empty or null in the configuration file; deleting DEM.")
    if (dir.exists(dem_source)) {
      unlink(dem_source, recursive = TRUE)
    }

  } else if (dem_output_dir == "dem") {
    message("DEM output dir is 'dem' - no action taken")

  } else {

    # if dem_output_dir does not exist, then create it
    if (!dir.exists(dem_output_dir)) {
      dir.create(dem_output_dir, recursive = TRUE, showWarnings = FALSE)
      message(glue("Created dem_output_dir: {dem_output_dir}"))
    }

    # move DEM if it exists
    if (dir.exists(dem_source)) {

      if (dir.exists(dem_target)) {
        unlink(dem_target, recursive = TRUE)
      }

      dir.create(dirname(dem_target), recursive = TRUE, showWarnings = FALSE)
      file.rename(dem_source, dem_target)

      message(glue("Moved DEM to {dem_target}"))

    } else {
      message(glue("DEM source does not exist: {dem_source}"))
    }

  }

}

