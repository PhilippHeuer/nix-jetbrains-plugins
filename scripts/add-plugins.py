#! /usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3.pkgs.requests python3.pkgs.json5 nix.out

# This script adds missing plugins to the plugins.json file.
# Since JetBrains no longer provides a list of all plugins, we have to manually discover them.

from argparse import ArgumentParser
import logging
from lib.plugins import read_plugins_config, write_plugins_config, get_plugin_info


def main():
  parser = ArgumentParser(description="Add missing plugins to plugins.json")
  parser.add_argument("pluginIds", metavar="N", type=int, nargs="*",
                      help="an integer for the plugin ID to add")
  args = parser.parse_args()
  logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


  logging.info("adding missing plugins to plugins.json")
  plugins = read_plugins_config()

  pluginIdRange = args.pluginIds if args.pluginIds else range(24000, 26001)
  for pluginId in pluginIdRange:
    if not any(p["id"] == pluginId for p in plugins):
      try:
        logging.info(f"adding new plugin {pluginId}")
        plugin_metadata = get_plugin_info(pluginId, "")

        id = plugin_metadata["id"]
        key = plugin_metadata["xmlId"]
        name = plugin_metadata["name"]
        downloads = plugin_metadata["downloads"]

        plugins.append({
          "id": id,
          "key": key,
          "name": name,
          "slug": name.lower().replace(" ", "-"),
          "downloads": downloads
        })
      except Exception as e:
        logging.error(f"failed to add plugin {pluginId}: {e}")

    if pluginId % 100 == 0:
      write_plugins_config(plugins)

  write_plugins_config(plugins)


if __name__ == '__main__':
  main()
