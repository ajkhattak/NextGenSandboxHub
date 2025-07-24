# @author Ahmad Jan Khattak
# @email ahmad.jan.khattak@noaa.gov
# @author Lauren Bolotin
# @email lauren.bolotin@noaa.gov
# @date  December 22, 2023

# The script downloads geopackge(s) given USGS gauge id(s) (also can read gpkg from the disk)
# Computes TWI, GIUH, Nash cascade parameters, and extracts model attributes from source,
# source could either be hydrofabric S3 endpoint or local sync hydrofabric (preferred for speed)

# INPUT  : yaml file (see below)
# OUTPUT : a geopackage with all model parameters, which is used for generating config and realization files

######################## REQUIRED INPUT #######################################
# Key steps are hihglight as:
# STEP #1: Setup (REQUIRED) (main.R)
# STEP #2: Options: Provide gage ID or list of gage IDs or set path to work with already download geopackages (main.R)
# Workflow substeps
#   STEP #3: Download geopackage (if needed) (inside driver.R)
#   STEP #4: Add model attributes to the geopackage (inside driver.R)
#   STEP #5: Compute TWI and width function (inside driver.R)
#   STEP #6: Compute GIUH (inside driver.R)
#   STEP #7: Compute Nash cascade parameters (N and K) for surface runoff (inside driver.R)
#   STEP #8: Compute terrain slope from the DEM (inside driver.R)
#   STEP #8a: Compute NLCD landcover (inside driver.R)
#   STEP #9: Append GIUH, TWI, width function, Nash cascade parameters, slope, and vegetation type to model_attributes layer (inside driver.R)


################################ SETUP #########################################
# STEP #1: INSTALL REQUIRED PACKAGES 
# - set sandbox_dir (basin_sandbox repository directory)
# - set options for installing/reinstalling hydrofabric and other packages 
# - set dem_infile (defaults to S3 .vrt file)
# - set output_dir (geopackages and DEM files will be stored here)

# - reinstall_hydrofabric    # Defaults to FALSE. TRUE updates/overwrites the existing hydrofabric
# - reinstall_arrow          # Defaults to FALSE. old arrow package or arrow installed without S3 support can cause issues, 
                             # typical error msg "Error: NotImplemented: Got S3 URI but Arrow compiled without S3 support"
                             # setting it to TRUE to install arrow package with S3 support 
                             # (see install_load_libs.R for more instructions)
# - dem_infile = "/vsicurl/https://lynker-spatial.s3.amazonaws.com/gridded-resources/dem.vrt"


library(yaml)
args <- commandArgs(trailingOnly = TRUE)

Setup <-function() {

  if (length(args) == 1) {
    infile_config = args
    print (paste0("Config file provided: ", infile_config))
  } else if (length(args) > 1) {
    stop("Please provide only one argument (input.yaml).")
  } else {
    infile_config <- "<path_to_sandboxhub>/configs/sandbox_config.yaml"
  } 

  if (!file.exists(infile_config)) {
    print(paste0("input config file does not exist, provided: ", infile_config))
    print ("Note: if running from RStudio, make sure infile_config points is set propely (line 54 in the main.R).")
    return(1)
  }

  inputs = yaml.load_file(infile_config)

  sandbox_dir   <<- inputs$sandbox_dir
  output_dir    <<- inputs$input_dir
  hf_version    <<- inputs$subsetting$hf_version
  hf_gpkg_path  <<- inputs$subsetting$hf_gpkg_path
  nproc         <<- inputs$subsetting$number_processors
  
  
  source(paste0(sandbox_dir, "/src/R/install_load_libs.R"))
  source(glue("{sandbox_dir}/src/R/custom_functions.R"))
  
  compute_divide_attributes <<- get_param(inputs, "subsetting$compute_divide_attributes", FALSE)
  
  # dem_input_file        <<- get_param(inputs, "subsettings$dem_input_file", "s3://lynker-spatial/gridded-resources/dem.vrt")
  # Newer DEM, better for oCONUS and other previously problematic basins
  dem_input_file  <<- get_param(inputs, "subsetting$dem_input_file", "s3://lynker-spatial/gridded-resources/dem.vrt")

  dem_output_dir  <<- get_param(inputs, "subsetting$dem_output_dir", "")

  # NLCD vegetation data parameters
  nlcd_data_path        <<- get_param(inputs, "subsetting$nlcd_data_path", FALSE)
  calculate_vegetation  <<- get_param(inputs, "subsetting$calculate_vegetation", FALSE)
  
  use_gage_id   <<- get_param(inputs, "subsetting$options$use_gage_id$use_gage_id", FALSE)
  gage_ids      <<- get_param(inputs, "subsetting$options$use_gage_id$gage_ids", NULL)
  
  use_gage_file <<- get_param(inputs, "subsetting$options$use_gage_file$use_gage_file", FALSE)
  gage_file     <<- get_param(inputs, "subsetting$options$use_gage_file$gage_file", NULL)
  column_name   <<- get_param(inputs, "subsetting$options$use_gage_file$column_name", "")
  
  use_gpkg      <<- get_param(inputs, "subsetting$options$use_gpkg$use_gpkg", FALSE)
  gpkg_dir      <<- get_param(inputs, "subsetting$options$use_gpkg$gpkg_dir", NULL)
  pattern       <<- get_param(inputs, "subsetting$options$use_gpkg$pattern", "Gage_")
  
  if (sum(use_gage_id, use_gage_file, use_gpkg) != 1){
    print(glue("setup error: one condition needs to be TRUE, user provided: \n
             use_gage_id   = {use_gage_id}, \n 
             use_gage_file = {use_gage_file}, \n 
             use_gpkg      = {use_gpkg}"))
    return(1)
  }
  
  if (!file.exists(output_dir)) {
    print(glue("Output directory does not exist, provided: {output_dir}"))
    return(1)
  }
  
  setwd(output_dir)
  wbt_wd(getwd())
  
  return(0)
}

# call setup function to read parameters from config file
tryCatch({
  Setup() 
}, error = function(e) {
  message("Setup failed: ", e$message)
  stop()
})

print ("SETUP DONE!")


################################ OPTIONS #######################################

start_time <- Sys.time()
if (use_gage_id == TRUE || use_gage_file == TRUE) {
  ################################ EXAMPLE 1 ###################################
  # For this example either provide a gage ID or a file to read gage IDs from
  # Modify this part according your settings
  
  if (use_gage_file == TRUE) {
    d = read.csv(gage_file,colClasses = c("character")) 
    gage_ids <- d[[column_name]]
      gage_ids <- zeroPad(gage_ids, 8)

  }
  
  stopifnot( length(gage_ids) > 0)

  DriverGivenGageIDs(gage_id = gage_ids, 
                    output_dir = output_dir,
                    nproc = nproc,
                    dem_output_dir = dem_output_dir,
                    dem_input_file = dem_input_file,
                    nlcd_data_path = nlcd_data_path,
                    calculate_vegetation = calculate_vegetation,
                    compute_divide_attributes = compute_divide_attributes
                    )
  
  
} else if (use_gpkg == TRUE) {

  gage_files = list.files(gpkg_dir, full.names = TRUE, pattern = pattern)
  
  DriverGivenGPKG(gage_files = gage_files, 
                  gpkg_dir   = gpkg_dir, 
                  output_dir = output_dir,
                  nproc = nproc,
                  dem_output_dir = dem_output_dir,
                  dem_input_file = dem_input_file,
                  nlcd_data_path = nlcd_data_path,
                  calculate_vegetation = calculate_vegetation,
                  compute_divide_attributes = compute_divide_attributes
                  )
}


end_time <- Sys.time()
time_taken <- as.numeric(end_time - start_time, units = "secs")
print (paste0("Total Time Taken = ", time_taken))

# check for failed basins
basins_failed <- glue("{output_dir}/basins_failed")

if (dir.exists(basins_failed)) {
  files <- list.files(basins_failed, full.names = TRUE)
  subdirs <- files[dir.exists(files)]
  if (length(subdirs) > 0) {
    subdir_names <- basename(subdirs)
    print("List of Basins failed..")
    print(subdir_names)
  }
  else {
    print ("All Basins Passed!!!")
  }
} 


################################### DONE #######################################
