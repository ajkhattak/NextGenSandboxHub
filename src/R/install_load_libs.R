######################### INSTALL REQUIRED PACKAGES ############################
# STEP #1: The packages need to run Hydrofabric tools for subsetting basins
################################################################################
#install.packages("renv")
#renv::init()

if (Sys.info()['sysname'] == "Windows") {
  options(download.file.method = "curl", download.file.extra="-k -L")
}


cran_packages <- c(
  "whitebox", "Metrics", "dplyr", "glue", "raster",
  "jsonlite", "ggplot2", "pbapply", "yaml",
  "dataRetrieval", "exactextractr", "sf", "terra"
)

github_packages <- c(
  "owp-spatial/hfsubsetR",
  "mikejohnson51/zonal"
)


installed <- rownames(installed.packages())

for (pkg in cran_packages) {
  if (!pkg %in% installed) {
    install.packages(pkg, dependencies = TRUE)
  }
}

if (!requireNamespace("remotes", quietly = TRUE)) {
  install.packages("remotes")
}

for (repo in github_packages) {
  pkg <- basename(repo)
  if (!requireNamespace(pkg, quietly = TRUE)) {
    remotes::install_github(repo, upgrade = "never")
  }
}

if (!whitebox::check_whitebox_binary()) {
  whitebox::install_whitebox()
}

suppressPackageStartupMessages({
  library(zonal)
  library(whitebox)
  library(sf)
  library(terra)
  library(exactextractr)
  library(dplyr)
  library(glue)
  library(raster)
  library(jsonlite)
  library(ggplot2)
  library(Metrics)
  library(pbapply)
  library(parallel)
  library(yaml)
  library(dataRetrieval)
})

###########
# if(!requireNamespace("remotes", quietly=TRUE))
#   install.packages("remotes")
# 
# if(!requireNamespace("hfsubsetR", quietly=TRUE))
#   remotes::install_github("owp-spatial/hfsubsetR")
# 
# if(!requireNamespace("zonal", quietly=TRUE))
#   remotes::install_github("mikejohnson51/zonal")
# 
# if(!requireNamespace("whitebox", quietly=TRUE)) {
#   install.packages("whitebox")
#   whitebox::install_whitebox()
# }
# 
# if(!requireNamespace("Metrics", quietly=TRUE))
#   install.packages("Metrics")
# 
# if(!requireNamespace("dplyr", quietly=TRUE))
#    install.packages("dplyr")
# 
# 
# if(!requireNamespace("glue", quietly=TRUE)) {
#   install.packages("glue")
# }
#   
# 
# if(!requireNamespace("raster", quietly=TRUE))
#    install.packages("raster")
# 
# if(!requireNamespace("jsonlite", quietly=TRUE))
#    install.packages("jsonlite")
# 
# if(!requireNamespace("ggplot2", quietly=TRUE))
#    install.packages("ggplot2")
# 
# if(!requireNamespace("pbapply", quietly=TRUE))
#    install.packages("pbapply")
# 
# if(!requireNamespace("yaml", quietly=TRUE))
#    install.packages("yaml")
# 
# if(!requireNamespace("dataRetrieval", quietly=TRUE)) 
#    install.packages("dataRetrieval")
# 
# if(!requireNamespace("exactextractr", quietly=TRUE)) 
#   install.packages("exactextractr")
# 
# library(zonal)
# library(whitebox)
# library(sf)
# library(terra)
# library(exactextractr)
# library(dplyr)
# suppressPackageStartupMessages(library(glue))
# library(raster)
# suppressPackageStartupMessages(library(raster))
# library(jsonlite)
# library(ggplot2)
# library(Metrics)
# library(pbapply)
# library(parallel)
# library(yaml)
# library(dataRetrieval)