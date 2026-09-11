# Environment Profile Validation

NextGenSandbox uses one environment-profile workflow on local computers and
HPC systems. From the repository root:

On HPC systems, use GCC with a matching GCC-built OpenMPI stack for the routine
build. Keep optional Intel builds in a distinct profile and
`SANDBOX_BUILD_DIR`; do not mix raw GNU compilers with Intel-backed MPI
wrappers.

```bash
cp configs/sandbox_profile.sh sandbox_profile.sh
source ./sandbox_profile.sh
./bootstrap.sh --check
```

The root-level profile is ignored by Git. Its defaults use `build/` and
`data/` under the repository. Before sourcing it on an HPC system, customize
the module commands and place `SANDBOX_BUILD_DIR` on project or scratch
storage.

The profile:

- locates the repository in Bash and zsh;
- exports the Sandbox build, data, environment, and ngen paths;
- selects loaded MPI compiler wrappers unless explicit compilers are set;
- derives `NETCDF_ROOT` from `nf-config` when available;
- activates an existing Conda environment or Python virtual environment;
- never modifies `.bashrc`, `.bash_profile`, or `.zshrc`.

Before `./bootstrap.sh --sandbox` has run, the profile reports that the Python
environment does not exist. This is expected. Build it and source the profile
again:

```bash
./bootstrap.sh --sandbox
source ./sandbox_profile.sh
```

The second source activates the new environment. Verify:

```bash
./bootstrap.sh --check
command -v sandbox
```

The check should report the loaded profile and should resolve `sandbox` inside
`$SANDBOX_ENV/bin`. Run the check after each major installation stage and
whenever a build or workflow command fails.

For separate compiler stacks, create one profile per stack and give each one a
distinct `SANDBOX_BUILD_DIR`, such as `build/gcc` and `build/intel`.
