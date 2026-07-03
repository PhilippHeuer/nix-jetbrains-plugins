# Nix plugins for JetBrains IDEs

Nixpkgs only contains a few of the more than 10,000 extensions in the [JetBrains Marketplace](https://plugins.jetbrains.com/).
This project provides Nix expressions for a curated list of popular extensions.

## Differences to nixpkgs

- added additional identifier (xmlPluginId -> `key`)
- disallow using the `name` to install plugins to avoid conflicts (recommendation: use unique attributes like `id` or `key` instead)

## Update Cycle

Run the update script:

```bash
./scripts/update-plugins.py
```

## Usage (Flakes)

Add the input to your `flake.nix`:

```nix
nix-jetbrains-plugins = {
  url = "github:PhilippHeuer/nix-jetbrains-plugins";
};
```

Then you can use the `addPlugins` function to add plugins to your IDE:

**Note**: You can search for plugins on the [JetBrains Marketplace](https://plugins.jetbrains.com/). The number in the URL is the `id` of the plugin, e.g. `164` for `https://plugins.jetbrains.com/plugin/164-ideavim`.

```nix
{ pkgs, pkgs-unstable, inputs, ... }:

let
  pluginList = [
    "164"    # ideavim
    "18682"  # catppuccin-theme
  ];

  addPlugins = (inputs.nix-jetbrains-plugins.import pkgs-unstable).addPlugins;
  idea-community = addPlugins pkgs-unstable.jetbrains.idea-community-bin pluginList;
in {
  environment.systemPackages = [
    idea-community
  ];
}
```

## Adding Plugins

Edit `data/plugin-ids.jsonc` to add or remove plugins from the curated list, then run `./scripts/update-plugins.py`.

## Credits / References

- https://github.com/NixOS/nixpkgs/tree/master/pkgs/applications/editors/jetbrains/plugins
- https://github.com/Cryolitia/nix-jetbrains-plugins

## License

Released under the [MIT License](./LICENSE).
