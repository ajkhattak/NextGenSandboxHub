library(sf)
library(dplyr)
library(stringr)
library(fs)

# Dir where the gpkgs are that you want to check/clean. This is also where new gpkgs will be saved.
input_dir <- "/Users/laurenbolotin/Lauren/probable-winner/ngen_delve/examples/percent_contribution"
gpkgs <- dir_ls(input_dir, glob = "*.gpkg")

# Function to process a single gpkg
process_gpkg <- function(gpkg_path) {
  cat("Processing:", gpkg_path, "\n")
  
  # Read the 'divides' layer
  divides <- st_read(gpkg_path, layer = "divides", quiet = TRUE)
  divides$component_id <- -1
  
  # Identify disconnected groups
  remaining <- divides
  group_id <- 0
  
  while (nrow(remaining) > 0) {
    seed <- remaining[1, ]
    touched <- seed
    previous_len <- -1
    
    while (nrow(touched) > previous_len) {
      previous_len <- nrow(touched)
      union_geom <- st_union(touched)
      touched <- remaining[st_touches(remaining, union_geom, sparse = FALSE)[,1] |
                             st_intersects(remaining, union_geom, sparse = FALSE)[,1], ]
    }
    
    indices <- which(divides$divide_id %in% touched$divide_id)
    divides$component_id[indices] <- group_id
    remaining <- remaining[!remaining$divide_id %in% touched$divide_id, ]
    group_id <- group_id + 1
  }
  
  # Calculate component areas
  divides$area <- st_area(divides)
  component_areas <- divides %>%
    group_by(component_id) %>%
    summarise(total_area = sum(area))
  
  # Skip if only one component (i.e., all divides fully connected)
  if (nrow(component_areas) == 1) {
    cat("  No disconnected divides found. Skipping.\n\n")
    return(NULL)
  }
  
  main_component_id <- component_areas$component_id[which.max(component_areas$total_area)]
  
  valid_divide_ids <- divides %>%
    filter(component_id == main_component_id) %>%
    pull(divide_id)
  
  invalid_divide_ids <- divides %>%
    filter(component_id != main_component_id) %>%
    pull(divide_id)
  
  # Skip if no invalid divides found (even if you have a multipolygon, they are connected)
  if (length(invalid_divide_ids) == 0) {
    cat("  No disconnected divides found. Skipping.\n\n")
    return(NULL)
  }
  
  # Just get the numeric id, not the cat- or wb- prefixes
  extract_numeric_id <- function(x) {
    as.integer(str_extract(x, "\\d+$"))
  }
  
  invalid_numeric_ids <- sapply(invalid_divide_ids, extract_numeric_id)
  
  # Prepare output file path
  temp_path <- str_replace(gpkg_path, "\\.gpkg$", "_cleaned.gpkg")
  file_copy(gpkg_path, temp_path, overwrite = TRUE)
  
  layers <- st_layers(gpkg_path)$name
  
  for (layer in layers) {
    
    gdf <- st_read(gpkg_path, layer = layer, quiet = TRUE)
    
    if (layer == "nexus") {
      cat("     (Skipping to maintain all nexi)\n")
    } else if ("divide_id" %in% colnames(gdf)) {
      gdf$numeric_id <- sapply(gdf$divide_id, extract_numeric_id)
      gdf <- gdf[!(gdf$numeric_id %in% invalid_numeric_ids), ]
      gdf$numeric_id <- NULL
    }
    
    # Write cleaned gpkg
    st_write(gdf, temp_path, layer = layer, driver = "GPKG", delete_layer = TRUE, quiet = TRUE)
  }
  
  cat("Wrote cleaned hydrofabric file:", temp_path, "\n\n")
}

# Run for all gpkgs in the input_dir
for (gpkg in gpkgs) {
  process_gpkg(gpkg)
}
