######################### INSTALL REQUIRED PACKAGES ############################
# STEP #1: The packages need to run Hydrofabric tools for subsetting basins
################################################################################

if (Sys.info()['sysname'] == "Windows") {
  options(download.file.method = "curl", download.file.extra="-k -L")
}

if(!requireNamespace("devtools", quietly=TRUE))
  install.packages("devtools")
if(!requireNamespace("curl", quietly=TRUE))
  install.packages("curl")
if(!requireNamespace("usethis", quietly=TRUE))
  install.packages("usethis")

suppressPackageStartupMessages({
  library(curl)
  library(usethis)
  library(devtools)
})

if(!requireNamespace("hydrofabric3D", quietly=TRUE))
  devtools::install_github("mikejohnson51/hydrofabric3D")

if(!requireNamespace("hydrofabric", quietly=TRUE)) {
  #devtools::install_github("noaa-owp/hydrofabric", ref = 'b07c109', force = TRUE)
  devtools::install_github("noaa-owp/hydrofabric", force = TRUE)
}

if(!requireNamespace("climateR", quietly=TRUE)) 
  devtools::install_github("mikejohnson51/climateR", force = TRUE)

if(!requireNamespace("zonal", quietly=TRUE))
  devtools::install_github("mikejohnson51/zonal", force = TRUE)

if(!requireNamespace("AOI", quietly=TRUE))
  devtools::install_github("mikejohnson51/AOI")

if(!requireNamespace("hfsubsetR", quietly=TRUE))
  remotes::install_github("owp-spatial/hfsubsetR")

if(!requireNamespace("sf", quietly=TRUE)) 
  install.packages("sf")

if(!requireNamespace("terra", quietly=TRUE)) 
  install.packages("terra")

if(!requireNamespace("whitebox", quietly=TRUE)) {
  install.packages("whitebox")
  whitebox::install_whitebox()
}

if(!requireNamespace("Metrics", quietly=TRUE)) 
  install.packages("Metrics")

if(!requireNamespace("dplyr", quietly=TRUE)) 
  install.packages("dplyr")

if(!requireNamespace("glue", quietly=TRUE)) 
  install.packages("glue")

if(!requireNamespace("raster", quietly=TRUE)) 
  install.packages("raster")

if(!requireNamespace("jsonlite", quietly=TRUE)) 
  install.packages("jsonlite")

if(!requireNamespace("ggplot2", quietly=TRUE)) 
  install.packages("ggplot2")

if(!requireNamespace("pbapply", quietly=TRUE)) 
  install.packages("pbapply")

if(!requireNamespace("yaml", quietly=TRUE)) 
  install.packages("yaml")

if(!requireNamespace("dataRetrieval", quietly=TRUE)) 
  install.packages("dataRetrieval")

# install arrow package from source, if any conflicts/errors happen due to arrow package
if(!requireNamespace("arrow", quietly=TRUE)) {
  # 1
  #Sys.setenv("NOT_CRAN" = "true")
  #Sys.setenv(LIBARROW_BINARY = TRUE)
  #install.packages('arrow', type = "source") 
  
  # 2
  Sys.setenv(NOT_CRAN=TRUE, LIBARROW_MINIMAL=FALSE, LIBARROW_BINARY=FALSE)
  install.packages("arrow", repos = "https://packagemanager.posit.co/cran/2024-04-01")

  # 3
  # if ran into arrow installation issues, once can try the following too.
  # S3 support not enabled for r-universe by default (https://github.com/apache/arrow/issues/43030)
  #install.packages("arrow", repos = 'https://apache.r-universe.dev') 
}
 

#library(hydrofabric)
suppressPackageStartupMessages(library(hydrofabric))
library(climateR)
library(zonal)
library(whitebox)
library(sf)
library(terra)
library(dplyr)
suppressPackageStartupMessages(library(glue))
#library(raster)
suppressPackageStartupMessages(library(raster))
library(jsonlite)
library(ggplot2)
library(Metrics)
suppressPackageStartupMessages(library(arrow))
library(pbapply)
library(parallel)
library(yaml)
library(dataRetrieval)

# put all packages in a list for the use in parallel execution
libraries_lst <- c(suppressPackageStartupMessages(library(hydrofabric)),
                   library(climateR),
                   library(zonal),
                   library(whitebox),
                   library(sf),
                   library(terra),
                   library(dplyr),
                   suppressPackageStartupMessages(library(glue)),
                   suppressPackageStartupMessages(library(raster)),
                   library(jsonlite),
                   library(ggplot2),
                   library(Metrics),
                   suppressPackageStartupMessages(library(arrow)),
                   library(RSQLite),
                   library(DBI),
                   library(pbapply),
                   library(parallel),
                   library(yaml)
                   )

# to sync hydrofabric to local machine
#local   <- "/Users/ahmadjan/Core/SimulationsData/preprocessing/hydrofabricS3"
#s3      <- "s3://lynker-spatial/hydrofabric"
#version <-  'v2.1.1'
#type    <- "nextgen"
#domain  <- "conus"

#(sys <- glue::glue("aws s3 sync {s3}/{version}/{type} {local}/{version}/{type}"))

