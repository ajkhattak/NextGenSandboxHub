############################### SET PATHS ######################################
# STEP #2. Load custom .R files
################################################################################

source(glue("{sandbox_dir}/src/R/twi_width.R"))
source(glue("{sandbox_dir}/src/R/helper.R"))
source(glue("{sandbox_dir}/src/R/giuh.R"))
source(glue("{sandbox_dir}/src/R/nash_cascade.R"))
source(glue("{sandbox_dir}/src/R/veg_type.R"))
source(glue("{sandbox_dir}/src/R/driver.R"))

# List all functions - give access to these function to each worker
functions_lst = c("RunDriver", "add_model_attributes", "dem_function", "twi_function", 
                  "width_function", "twi_pre_computed_function", "giuh_function", 
                  "Nash_Cascade_Runoff", "get_nash_params", "fun_crop_lower", 
                  "fun_crop_upper", "clean_move_dem_dir")