Place a true multi-stem MVSep model here:

- config.yaml
- checkpoint.ckpt

The config must output accordion, piano, and other as separate stems.
It must not be an accordion-only target model with target_instrument: accordion.

To download the model during setup, add download-urls.txt in this folder before building.
Use this format:

config_url=https://example.com/path/to/config.yaml
checkpoint_url=https://example.com/path/to/checkpoint.ckpt
