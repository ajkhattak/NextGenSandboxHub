## Supported Formulations
*Note:* Formulations may omit T-ROUTE; it is appended automatically by the workflow. However, all other model components must match the supported formulations exactly.

### CFE-S Formulations
*Conceptual Functional Equivalent with Schaake Runoff Option*
- NOM, CFE-S, T-ROUTE
- PET, CFE-S, T-ROUTE
- NOM, PET, CFE-S, T-ROUTE
- NOM, CFE-S, SMP, SFT, T-ROUTE
- SNOW17, PET, CFE-S, T-ROUTE

### CFE-X Formulations 
*Conceptual Functional Equivalent with Xinanjiang Runoff Option*

- NOM, CFE-X, T-ROUTE
- PET, CFE-X, T-ROUTE
- NOM, PET, CFE-X, T-ROUTE
- NOM, CFE-X, SMP, SFT, T-ROUTE
- SNOW17, PET, CFE-X, T-ROUTE

### TOPMODEL
- NOM, TOPMODEL, T-ROUTE
- PET, TOPMODEL, T-ROUTE
- NOM, PET, TOPMODEL, T-ROUTE
- SNOW17, PET, TOPMODEL, T-ROUTE

### CASAM 
*LGAR-based catchment-scale rainfall-runoff model*

- NOM, CASAM, T-ROUTE
- PET, CASAM, T-ROUTE
- SNOW17, PET, CASAM, T-ROUTE *(not tested yet)*
- NOM, CASAM, SMP, SFT, T-ROUTE *(not tested yet)*

### Sac-SMA
- SNOW17, PET, SAC-SMA

### ML-Based models
- LSTM

## Supported Models — Source Code Links

Here are the hydrologic and hydraulic modules supported by NextGenSandboxHub, along with links to their source-code repositories.

| Model / Module | GitHub Repository |
|----------------|------------------|
| NOM (Noah-OWP-Modular) | https://github.com/NOAA-OWP/noah-owp-modular |
| CFE (CFE-S / CFE-X) | https://github.com/NOAA-OWP/cfe |
| TOPMODEL | https://github.com/NOAA-OWP/topmodel |
| Snow-17 | https://github.com/NOAA-OWP/snow17 |
| PET (Potential Evapotranspiration) | https://github.com/NOAA-OWP/evapotranspiration |
| Sac-SMA | https://github.com/NOAA-OWP/sac-sma |
| CASAM (LGAR-based rainfall–runoff model) | https://github.com/NOAA-OWP/LGAR-C |
| LSTM (ML-based streamflow) | https://github.com/NOAA-OWP/lstm |
| SFT (SoilFreezeThaw) | https://github.com/NOAA-OWP/soilfreezethaw |
| SMP (SoilMoistureProfiles) | https://github.com/NOAA-OWP/soilmoistureprofiles |
| T-ROUTE (Routing) | https://github.com/NOAA-OWP/t-route |
