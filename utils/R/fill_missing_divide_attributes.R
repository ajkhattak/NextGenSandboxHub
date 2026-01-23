library(sf)
library(dplyr)
library(glue)
library(terra)

# Set the following paths
infile       <- "/Users/ahmadjankhattak/Core/input_data/hf2.2_gpkgs/conus_nextgen.gpkg"
outfile      <- "/Users/ahmadjankhattak/Core/input_data/hf2.2_gpkgs/conus_nextgen_updated2.gpkg"
dem_vrt_file <- "s3://lynker-spatial/gridded/3DEP/USGS_seamless_DEM_13.vrt"


# Fill Missing Divide Attributes
# Identifies divides with missing attributes (mostly coastal) and assigns values
# based on neighboring divides within the same VPU (Vector Processing Unit).

fill_missing_divide_attrs <- function(
    infile,
    outfile,
    id_col = "divide_id") 
  {
  
  # Read all layers
  all_layers <- st_layers(infile)$name
  
  check_divs  <- st_read(infile, layer = 'divides', quiet = TRUE)
  check_attrs <- st_read(infile, layer = 'divide-attributes', quiet = TRUE)
  
  # Ensure divide_id columns are character to avoid bind_rows errors
  check_divs[[id_col]] <- as.character(check_divs[[id_col]])
  check_attrs[[id_col]] <- as.character(check_attrs[[id_col]])
  
  # Identify missing rows
  missing_in_attrs <- setdiff(check_divs[[id_col]], check_attrs[[id_col]])
  
  if(length(missing_in_attrs) > 0) {

    # Filter missing coastal divides
    coastal_missing <- check_divs %>%
      filter(divide_id %in% missing_in_attrs & type == "coastal")
    
    if(nrow(coastal_missing) > 0) {
      
      # Initialize empty character dataframe
      missing_coastal_neighbors <- data.frame(
        coastal_divide_id = character(),
        nearest_divide_id = character(),
        stringsAsFactors = FALSE
      )
      
      # Loop over each VPU
      print ("unique vpuid")
      print (unique(coastal_missing$vpuid))
      
      for(vpu in unique(coastal_missing$vpuid)) {
        print (glue("VPU: {vpu}"))
        coastal_vpu <- coastal_missing %>% filter(vpuid == vpu)
        non_coastal_vpu <- check_divs %>% filter(type == "network" & vpuid == vpu)
        
        if(nrow(non_coastal_vpu) > 0) {
          nearest_idx <- st_nearest_feature(coastal_vpu, non_coastal_vpu)
          
          new_rows <- data.frame(
            coastal_divide_id = coastal_vpu[[id_col]],
            nearest_divide_id = non_coastal_vpu[[id_col]][nearest_idx],
            stringsAsFactors = FALSE
          )
          
          missing_coastal_neighbors <- bind_rows(missing_coastal_neighbors, new_rows)

        }
      }
      
      # Copy attributes from nearest neighbors
      attrs_to_copy <- missing_coastal_neighbors %>%
        left_join(check_attrs, by = c("nearest_divide_id" = "divide_id")) %>%
        dplyr::mutate(!!id_col := coastal_divide_id) %>%
        dplyr::select(all_of(names(check_attrs)))
    
      # Combine with original attributes
      check_attrs_updated <- bind_rows(check_attrs, attrs_to_copy)
      } else {
        check_attrs_updated <- check_attrs
        }
  } else {
    check_attrs_updated <- check_attrs
  }
  
  # Write all layers to new outfile
  for(layer_name in all_layers) {
    if(layer_name == "divide-attributes") {
      st_write(check_attrs_updated, outfile, layer = layer_name, delete_layer = TRUE)
    } else {
      layer_data <- st_read(infile, layer = layer_name, quiet = TRUE)
      st_write(layer_data, outfile, layer = layer_name, delete_layer = TRUE)
    }
  }
  
  message(glue("All layers written to {outfile}, with updated divide-attributes."))
  invisible(check_attrs_updated)
}



################################################################################
# Fix Stray Divide Geometries
# Identifies and corrects stray divide geometries, including semi-closed
# polygons and divides with open or dangling endpoints.
 
fix_divides_geometry <- function(
    infile,                   # path to the GeoPackage
    layer_name = 'divides',   # layer to fix
    dem_raster_file = NULL,   # optional: raster for CRS reference
    overwrite = TRUE,         # whether to overwrite the layer
    quiet = FALSE
) {
  
  stopifnot(file.exists(infile))
  
  # Read the layer
  div <- read_sf(infile, layer = layer_name)
  
  # Optionally transform CRS to match raster
  if (!is.null(dem_raster_file)) {
    elev <- rast(dem_raster_file)
    div <- st_transform(div, crs = crs(elev))
  }

  
  # Identify invalid geometries
  invalid_rows <- which(!st_is_valid(div))
  
  if (length(invalid_rows) > 0) {
    message("Fixing ", length(invalid_rows), " invalid geometries...")
    div <- st_make_valid(div)
  } else {
    message("All geometries in layer '", layer_name, "' are valid.")
    return()
  }
  
  st_write(div, infile, layer = layer_name,
    delete_layer = TRUE,   # deletes only this layer
    quiet = quiet
  )
  
  message("Layer '", layer_name, "' successfully updated in:\n  ", infile)
  
  invisible(div)
}



# Call fill missing 
fill_missing_divide_attrs(infile, outfile)

fix_divides_geometry(infile = outfile, layer_name = "divides", dem_raster_file = dem_vrt_file)

# Sanity checks

any(!st_is_valid(read_sf(outfile, "divides")))

