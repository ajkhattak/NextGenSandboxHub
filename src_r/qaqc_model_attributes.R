# @author Lauren Bolotin
# @email lauren.bolotin@noaa.gov
# @date  December 10, 2024

# This script does QA/QC on model attributes in geopackages downloaded using 
# the basin workflow

# INPUT  : yaml file (see below)
# OUTPUT : a csv file summarizing which basins failed to pass QA/QC, and which attributes were the source of the problem

library(yaml)
library(stringr)
library(sf)
args <- commandArgs(trailingOnly = TRUE)

setup <-function() {
  
  if (length(args) == 1) {
    infile_config = args
    print (paste0("Config file provided: ", infile_config))
  } else if (length(args) > 1) {
    stop("Please provide only one argument (input.yaml).")
  } else {
    infile_config <- "~/Lauren/basin_workflow/configs/config_workflow.yaml"
    model_attr_names <<- read.table("~/Lauren/basin_workflow/configs/basefiles/model_attribute_names.txt",
                                    header = TRUE)
  }
  
  if (!file.exists(infile_config)) {
    print(paste0("input config file does not exist, provided: ", infile_config))
    return(1)
  }
  
  inputs = yaml.load_file(infile_config)

  workflow_dir      <<- inputs$workflow_dir
  output_dir        <<- inputs$input_dir
  reinstall_hydrofabric <<- inputs$gpkg_model_params$reinstall_hydrofabric
  reinstall_arrow   <<- inputs$gpkg_model_params$reinstall_arrow

  source(paste0(workflow_dir, "/src_r/install_load_libs.R"))
  
  if (!file.exists(output_dir)) {
    print(glue("Output directory does not exist, provided: {output_dir}"))
    return(1)
  }
  
  setwd(output_dir)
  wbt_wd(getwd())
  
  return(0)
}

setup()

# Create QA/QC Functions ------------------------------------------------------
check_nwm_attrs <- function(){
  nwm_attrs <- c("mode.bexp_soil_layers_stag.1", "mode.ISLTYP", "mode.IVGTYP",
                 "mean.refkdt", "mean.Coeff", "mean.Zmax", "mode.Expon",
                 "mean.elevation", "mean.slope")
  # Do they exist?
  # Find out if any of the vars listed in nwm_attrs is missing from model_attributes
  missing_vars <- nwm_attrs[!nwm_attrs %in% colnames(model_attributes)]
  
  # If any are missing, print an error
  if (length(missing_vars) > 0) {
    for (var in missing_vars) {
      failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
      failed_attrs[[length(failed_attrs) + 1]] <<- var
      failed_reason[[length(failed_reason) + 1]] <<- "Missing"
    }
    stop(paste0("Missing NWM attributes in geopackage: ", infile, " - ", missing_vars))
  }
  
  # Check if any of the nwm_attrs are NA or NaN
  failed_nwm_attrs <<- list()
  for (attr in nwm_attrs) {
    if (any(is.na(model_attributes[[attr]])) | any(is.nan(model_attributes[[attr]]))) {
      # Add the name of this attr to the failed_nwm_attrs list
      failed_nwm_attrs[[length(failed_nwm_attrs) + 1]] <<- attr
      # Add the names of the attributes with any NA or NaN's to the failed_attrs list
      failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
      failed_attrs[[length(failed_attrs) + 1]] <<- attr
      failed_reason[[length(failed_reason) + 1]] <<- "NA value(s)"
      cat ("NA or NaN found in ", attr, " in geopackage: ", infile, "\n")
    }
  }
}
check_giuh <- function(){
  # Does it exist?
  if ("giuh" %in% colnames(model_attributes)) {
    giuh <- model_attributes$giuh
  } else {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "GIUH"
    failed_reason[[length(failed_reason) + 1]] <<- "Missing"
    stop(paste0("GIUH not found in geopackage: ", infile))
  }
  # Is it NA or NaN?
  if (any(is.na(giuh)) | any(is.nan(giuh))) {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "GIUH"
    failed_reason[[length(failed_reason) + 1]] <<- "NA value(s)"
    stop(paste0("NA or NaN found in GIUH in geopackage: ", infile))
  }
  # Extract the actual values
  # Use str_extract_all to extract each ordinate within curly brackets
  giuh_ords <- str_extract_all(giuh, "\\{[^\\}]+\\}")
  # Use str_extract to extract the number after "frequency": and before the closing }
  frequencies <- lapply(giuh_ords, function(x) str_extract(x, '(?<=\\"frequency\\":)[^}]+'))
  
  # Sum up each set of values 
  sums <- lapply(frequencies, function(x) sum(as.numeric(x)))
  
  # Print an error if the sums are NA or not equal to 1 +/- 0.01
  if (any(is.na(sums))){
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "GIUH"
    failed_reason[[length(failed_reason) + 1]] <<- "Missing frequency(ies)"
    stop(paste0("GIUH sums contain NA: ", infile))
  } else if (any(sums < 0.99) | any(sums > 1.01)) {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "GIUH"
    failed_reason[[length(failed_reason) + 1]] <<- "Unreasonable value(s)"
    stop(paste0("GIUH sums are not equal to 1 in geopackage: ", infile))
  }
  
  rm(giuh, giuh_ords, frequencies, sums)
}

check_twi <- function(){
  # Does it exist?
  if ("twi" %in% colnames(model_attributes)) {
    twi <- model_attributes$twi
  } else {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "TWI"
    failed_reason[[length(failed_reason) + 1]] <<- "Missing"
    stop(paste0("TWI not found in geopackage: ", infile))
  }
  
  # Is it NA or NaN?
  if (any(is.na(twi)) | any(is.nan(twi))) {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "TWI"
    failed_reason[[length(failed_reason) + 1]] <<- "NA value(s)"
    stop(paste0("NA or NaN found in TWI in geopackage: ", infile))
  }
  
  # Extract the actual values
  # Use str_extract_all to extract each ordinate within curly brackets
  twi_ords <- str_extract_all(twi, "\\{[^\\}]+\\}")
  
  # Use str_extract to extract the number after "v\": and before ,\"frequency"
  v <- lapply(twi_ords, function(x) str_extract(x, "(?<=\"v\":)[0-9.]+"))
  
  # Use str_extract to extract the number after "frequency": and before the closing }
  frequencies <- lapply(twi_ords, function(x) str_extract(x, '(?<=\\"frequency\\":)[^}]+'))
  
  # Sum up each set of values
  sums <- lapply(frequencies, function(x) sum(as.numeric(x)))
  
  # Print an error if the sums are NA or not equal to 1 +/- 0.01
  if (any(is.na(sums))){
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "TWI"
    failed_reason[[length(failed_reason) + 1]] <<- "Missing frequency(ies)"
    stop(paste0("TWI sums contain NA: ", infile))
  } else if (any(sums < 0.99) | any(sums > 1.01)) {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "TWI"
    failed_reason[[length(failed_reason) + 1]] <<- "Unreasonable value(s)"
    stop(paste0("TWI sums are not equal to 1 in geopackage: ", infile))
  }
  
  rm(twi, twi_ords, v, frequencies, sums)
}

check_width <- function(){
  # Does it exist?
  if ("width_dist" %in% colnames(model_attributes)) {
    width <- model_attributes$width_dist
  } else {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "width"
    failed_reason[[length(failed_reason) + 1]] <<- "Missing"
    stop(paste0("Width not found in geopackage: ", infile))
  }
  
  # Is it NA or NaN?
  if (any(is.na(width)) | any(is.nan(width))) {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "width"
    failed_reason[[length(failed_reason) + 1]] <<- "NA value(s)"
    stop(paste0("NA or NaN found in Width in geopackage: ", infile))
  }
  
  # Extract the actual values
  # Use str_extract_all to extract each ordinate within curly brackets
  width_ords <- str_extract_all(width, "\\{[^\\}]+\\}")
  
  # Use str_extract to extract the number after "v\": and before ,\"frequency"
  v <- lapply(width_ords, function(x) str_extract(x, "(?<=\"v\":)[0-9.]+"))
  # Use str_extract to extract the number after "frequency": and before the closing }
  frequencies <- lapply(width_ords, function(x) str_extract(x, '(?<=\\"frequency\\":)[^}]+'))
  
  # Sum up each set of values
  sums <- lapply(frequencies, function(x) sum(as.numeric(x))) 
  
  # Print an error if the sums are NA or not equal to 1 +/- 0.01
  if (any(is.na(sums))){
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "width"
    failed_reason[[length(failed_reason) + 1]] <<- "Missing frequency(ies)"
    stop(paste0("Width sums contain NA: ", infile))
  } else if (any(sums < 0.99) | any(sums > 1.01)) {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "width"
    failed_reason[[length(failed_reason) + 1]] <<- "Unreasonable value(s)"
    stop(paste0("Width sums are not equal to 1 in geopackage: ", infile))
  }
  
  rm(width, width_ords, v, frequencies, sums)
}

check_n_nash <- function(){
  # Does it exist?
  if ("N_nash_surface" %in% colnames(model_attributes)) {
    n_nash <- model_attributes$N_nash_surface
  } else {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "N_nash"
    failed_reason[[length(failed_reason) + 1]] <<- "Missing"
    stop(paste0("N_nash_surface not found in geopackage: ", infile))
  }
  
  # Is it NA or NaN?
  if (any(is.na(n_nash)) | any(is.nan(n_nash))) {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "N_nash"
    failed_reason[[length(failed_reason) + 1]] <<- "NA value(s)"
    stop(paste0("NA or NaN found in N_nash_surface in geopackage: ", infile))
  }
  
  # Check if any values are something besides 2 or 5
  valid_n_nash <- all(n_nash %in% c(2, 5))
  
  # Print the result
  if (!valid_n_nash) {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "N_nash"
    failed_reason[[length(failed_reason) + 1]] <<- "Unreasonable value(s)"
    stop(paste0("N_nash_surface values are neither 2 or 5 in geopackage: ", infile))
  }
  
  rm(n_nash)
}

check_k_nash <- function(){
  # Does it exist?
  if ("K_nash_surface" %in% colnames(model_attributes)) {
    k_nash <- model_attributes$K_nash_surface
  } else {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "K_nash"
    failed_reason[[length(failed_reason) + 1]] <<- "Missing"
    stop(paste0("K_nash_surface not found in geopackage: ", infile))
  }
  
  # Is it NA or NaN?
  if (any(is.na(k_nash)) | any(is.nan(k_nash))) {
    failed_cats[[length(failed_cats) + 1]] <<- paste(basin)
    failed_attrs[[length(failed_attrs) + 1]] <<- "K_nash"
    failed_reason[[length(failed_reason) + 1]] <<- "NA value(s)"
    stop(paste0("NA or NaN found in K_nash_surface in geopackage: ", infile))
  }
}

################################ OPTIONS #######################################

# Run QA/QC Functions ---------------------------------------------------------
# Extract the list of basins we have gpkgs for
basins <- list.files(output_dir)

# Remove anything that's not numeric
basins <- basins[str_detect(basins, "^[0-9]+$")]

# basin <- "15294005" # for testing a specific basin
# Create an empty list to append basins with QA/QC issues to 
failed_cats <- list()
failed_attrs <- list()
failed_reason <- list()
failed_cats_list <- list()

# Loop through each basin and apply QA/QC checks
for (basin in basins) {
  tryCatch({
    # Read the geopackage -------------------
    infile <- glue('{output_dir}/{basin}/data/gage_{basin}.gpkg')
    # print (paste0("Reading geopackage: ", basename(infile)))
    model_attributes <- suppressWarnings(st_read(infile, layer = "divide-attributes", quiet = TRUE))
    
    check_nwm_attrs()
    check_giuh()
    check_twi()
    check_width()
    check_n_nash()
    check_k_nash()
    
  }, error = function(e) {
    # Handle error: print message and skip to the next iteration
    cat("Error with catchment:", basin, "\n")
    # Print which of the above functions had an error: 
    cat(e$message, "\n")
    failed_cats_list[[length(failed_cats_list) + 1]] <<- basin
    return(NULL)
  })
  
}

# Extract just the basin ids from failed_cats
failed_cats <- sapply(failed_cats, function(x) str_extract(x, "[0-9]+"))
# Make a dataframe with failed_cats in one column and failed_attrs in another
failed_df <- data.frame(basin = failed_cats, failed_attrs = unlist(failed_attrs),
                        failed_reason = unlist(failed_reason))

# Write the dataframe to a csv file only if it is not empty
if (nrow(failed_df) == 0) {
  print("No basins failed QA/QC")
} else {
  print(glue("Basins failed QA/QC: {failed_df$basin}"))
  write.csv(failed_df, glue("{output_dir}/failed_basin_attrs.csv"), row.names = FALSE)
}
