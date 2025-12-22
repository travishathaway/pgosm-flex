# Notes on porting to non-docker

These are some notes I took while trying to get this running outside of docker.

## Setting up the conda environment

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

I had to add a special `--base-path` argument that's just a temporary work around so that the command is able
to find all the files it needs.

You also need to make sure that your data user has `superuser` privileges, so it can create everything (more restricted
privileges are probably possible, but I did not want to identify these all by hand).

This is the command I'm currently using to run an import for Berlin, Germany:

```
python docker/pgosm_flex.py --schema-name pgosm --region=europe/germany --subregion=berlin --ram=6 --base-path=/home/<thath>/dev/pgosm-flex/ --layerset-path=/home/<user>/dev/pgosm-flex/flex-config/layerset/
```


