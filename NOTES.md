# Notes on porting to non-docker

These are some notes I took while trying to get this running outside of docker.

## 2025-12-06: Setting up the conda environment

Here's the command to set up the conda environment

Fetch the remote tags (otherwise this will cause an error later):

```commandline
git fetch
```

```
conda create --name pgosm-flex \
  --override-channels \
  --channel conda-forge \
  --channel /home/<user>/opt/conda-local-channel \
  python=3.13 \
  pip \
  osmium-tool \
  osm2pgsql \
  luarocks
```

After you have that environment setup, you have to run these two commands to
install `pypi` and `luarocks` dependencies.

Python:

```
pip install -r requirements.txt
```

Lua:

```
luarocks install inifile
luarocks install luasql-postgres PGSQL_DIR=/home/<user>/opt/conda/envs/pgosm-flex/
```

Additionally, you have to set the following environment variables:

(these would normally be set by docker)

```
export POSTGRES_USER=user
export POSTGRES_PASSWORD=password
export POSTGRES_DB=pgosm
```

I had to add a special `--base-path` argument that's just a temporary work around so that
the command is able to find all the files it needs.

You also need to make sure that your data user has `superuser` privileges, so it can create everything
(more restricted privileges are probably possible, but I did not want to identify these all by hand).

This is the command I'm currently using to run an import for Berlin, Germany:

```
python docker/pgosm_flex.py --schema-name pgosm --region=europe/germany --subregion=berlin --ram=6 --base-path=/home/<thath>/dev/pgosm-flex/ --layerset-path=/home/<user>/dev/pgosm-flex/flex-config/layerset/
```


## 2026-01-24: Updates on non-docker version

Recently, I moved the code around so it looks more like a traditional Python project
and added a `pyproject.toml` file. Some of the things I've done to the code itself is
trying to remove any unnecessary dependencies and subshell commands when possible.

Here's a couple examples of how I'm addressing this:

- **Remove dependency on GitPython**
  - This was being used to essentially get the current version of the project so that it
    can be saved with the data import. I'm moving the project to use actual version numbers,
    so this isn't necessary anymore.
- **Remove subshell calls for `md5`**
  - Python has built-in support for this via `hashlib` so it made sense to remove this. This
    will help us port it Windows.
- **Remove subshells calls for `wget`**
  - This is another thing that I feel is better handled by Python libraries, so I added a depedency
    on `httpx` to replace this.

### Wishlist going forward: possible beta release

#### Add missing conda-forge packages

- osmium (python bindings)

#### Configuration refactors

The configuration for the project could be improved by adding a central `config` module. Right now,
everything appears to be tucked away in `helpers`. By separating this out, I hope to achieve the
following:

- Separation of concerns to read code easier
- Introduce a `pgosm-flex.toml` file that can be used to configure projects
  - The CLI tool would recognize this file in the current directory and use these values as deafults
    when running the `pgosm-flex` command.
- Introduce `pydantic` as a dependency to help parse this file.

claude-code prompt:

> There's a python application in this folder called pgosm_flex and it currently makes use of enviroment variables and command line
> options to set its configuration. I'd like to expand this to include configuration values from a file called `pgosm-flex.toml` that
> would be located in the current directory. But, before we do this, we need to refactor the code so that it adds pydantic to help us
> handling the configuration file parsing and I would like all the logic for the configuration to live in a module called "config".
> A lot  of the existing logic for parsing configuration is in "helpers.py". Can you come up with a plan to refactor this code and
> enable this  new feature of being able to set configuration values in a toml file?

##### Status

I'm still working on this part and properly disentangling the config from purely relying on environment variables.

#### Create a data directory for managing downloads

The place where the CLI downloads and stores its data should be in an OS friendly spot using
the `platformdirs` package.

- Default should be in a spot determined by `platformdirs`
- Users should be able to override this by a configuration setting

##### Status

Not complete

#### Setup pre-commit, linters and type hinters

To ensure consistent coding style, I will introduce the same type of pre-commit hooks and linters
that I did for `zensus2pgsql`.

##### Status

Not complete

#### Make integration tests work without using the Dockerfile in this repository

The Dockerfile is doing a lot of things to build actual environment that the import script
has to run in. Once everything has been packaged as conda packages, I'll be able to just
bootstrap the Docker image with conda and install all the packages I need from conda-forge.

##### Status

I was able to get this started but still need to finish it by getting a working example up and
running.

The part that I was missing that I worked on was having all of this projects dependencies available
as conda dependencies. I was able to complete this part and now everything is saved in the
`~/opt/conda-local-channel`.


## 2026-01-26: remove lua

After studying the code so more, I noticed that there's a lot of logic in lua that doesn't need to
be. I might be oversimplifying, but it looks like it's just running a bunch SQL files in a 
for-loop. I think we can just move all this to Python to remove the dependency on lua altogether.
Right now, the installation is a little cumbersome because you have to install pypi dependencies
(these will eventually all be available as conda dependencies) and you have to install two
lua packages via `luarocks`.
