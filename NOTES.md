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

This part is more-or-less complete. I'm not sure if I like the current setup of calling a `get_config` function
everytime I need the config, but I think it's good enough for now.

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

After studying the code some more, I noticed that there's a lot of logic in lua that doesn't need to
be. I might be oversimplifying, but it looks like it's just running a bunch of SQL files in a 
for-loop. I think we can just move all this to Python to remove the dependency on lua altogether.
Right now, the installation is a little cumbersome because you have to install pypi dependencies
(these will eventually all be available as conda dependencies) and you have to install two
lua packages via `luarocks`.


## 2026-02-03: add postgresql tasks to pixi

Thankfully, support for postgis has been added for `osx-arm64`! I tried my best to add support, but
in the end the maintainers of that feedstock did it for me. Very happy to have it supported now.

Now that's in place, I can add some development tasks to the `pixi.toml` to start and stop postgresql.

Here's what I would like these development tasks to do:

- Create a postgresql database and initialize a new database with postgis enabled
  - Should choose a high port number that is available and should report this to the
    user somehow (maybe write settings to a pgosm-flex.toml?)
- Destroy a postgresql database
- Start the database
- Stop the database

I would also like this to be used in the integration tests.

#### Status

Done. There are now several new pixi tasks for starting and stopping postgresql:

- pg:destroy
- pg:shell
- pg:start
- pg:status
- pg:stop


## 2026-02-06: completing the integration tests

Today, I'm working on completing the integration tests so that they use `pytest-xprocess` to launch
and stop a `postgresql` server automatically while running the tests. I've also added a couple new
`pixi` tasks to control the running of these tests (e.g. `pixi run test-unit` and `pixi run test-integration`).

### Next steps

Once I can successfully run all the integration tests, I'll be ready to start manually testing out 
importing some real-world data. I'll start off with the Bremen and Berlin datasets because they are 
relatively small.

Another thing I can move on to is testing the update/replication functionality. I think this wasn't
covered at all in the original integration tests and could be a nice addition.

### A little later that same day...

The more I dug into the integration tests the more I realized that I want to overhaul them myself.
The main problem is that the `pgosm-flex` command isn't actually being tested from the top down.
As I was writing some tests to do this, I realized that everything is still utterly broken and I
need to spend some time running the `pgosm-flex` command manually to address all the issues.

The first one I want to tackle is the commands that attempts to drop the database completely. I'd
like to have a lighter touch here and simply remove all the tables instead and prompt the user
before doing so while also adding a `-f/--force` option.


## 2026-02-07: everything kind of works now

I now have a very basic happy path working for the tool. I'm using the `tests/data/district-of-columbia-2021-01-13.osm.pbf`
file to make sure that all the importing logic works. Now, I'm ready to automate this with my own integration
tests.

### No more luarocks dependencies

I really wanted to ensure that the lua scripts had zero external dependencies. This makes it, so I don't
have to install them separately. In conda environment this is definitely possible with `luarocks`, but
I want to avoid it to have fewer moving parts.

To get rid of it, I now dynamic load the configuration for the lua scripts in an environment variable
called `PGOSM_LUA_CONFIG`. This does present certain security issues (config values can be coerced into
executing arbitrary code now), but for now, I'm not worried about it and will make sure to mention this
later in any audits I do of my own work.

I did think about writing a config file to a temp location and then just loading that, but I think the
same security problems exist, and I would additionally have to handle dynamically loading this from
within the lua scripts themself.

### Later that day...

I was able to get the simple integration tests to work. The next steps are to add more and more scenarios
to make sure that everything is covered. The next two scenarios I'll focus on are actually downloading
geofabrik files by using the `--region` and `--subregion` options and testing the `--pg-dump` option.

### Random notes

- Don't think the `layerset` option is working when set from the config file
- Need to test:
  - `pg_dump`
  - `osm2pgql-replication`
  - loading settings from all different configuration sources
  - Downloading data from geofabrik
- Not sure if the new drop tables routine works as expected
- Something is creating `checksum-test.txt` files and I need to figure out why


## 2026-02-11: Planning for integration testing

I've been working on measuring and increasing the test coverage on the code of the last couple of days.
As of now, I've got ~81% coverage on this project. Most of the things left to cover are the various
error cases that can occur with various configurations. I also still need to cover the `--update=append/create`
cases.

One of the last things remaining to be changed is the `drop_db` behavior. For this project, I've decided
to not actually drop/create the database. This is something that I prefer to handle externally from the
CLI program. Instead, the program will simply drop tables from the specified schema. This a safer action
because it's only targeting a single schema in a database. Because of that, I want to enable dropping
on more than just `localhost`. The `localhost` only behavior is a leftover from the Docker setup that
I want to get rid of.

### Random notes

- Setup integration tests to run pgosm-flex as a non-superuser
- Need to test the `--force` option when the database already has tables in it


## 2026-02-14

### Random notes

- Setting the SRID from the configuration file doesn't work (fixed)
  - This error had to do with how I was setting defaults in the CLI options.
  - Because we have defaults set in the config system now, I've removed all
    the defaults from the CLI options.
- Need to add test that set values from the configuration file
  - This should be done in an integration test


## 2026-02-22

Today, I'd like to write some tests that focus on what it's like to work with an existing
database with tables loaded into it. Here are the scenarios I'll focus on:

- Using the `--force` option
  - This will essentially just run the loading twice. Once without `--force` and then once
    with `--force`
- Using the `--replication` twice; once with a dataset that's six days old and once with
  a datatset from today.

### Random notes

Before showing the project to the original maintainer, I'd like to get a working CI test system
in place with GHA. I think this is going to be a very compelling reason to accept the changes I've
made. But, before this happens, I need to wait on all the changes necessary to get this running
correctly in conda-forge.


