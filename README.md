# Nix plugins for JetBrains IDEs

Nixpkgs only contains a few of the more than 10,000 extensions in the [Jetbrains Marketplace](https://plugins.jetbrains.com/).
This project provides Nix expressions for all of the available extensions from the [Jetbrains Marketplace](https://plugins.jetbrains.com/).

## Differences to nixpkgs

- added additional identifier (xmlPluginId -> `key`)
- disallow using the `name` to install plugins to avoid conflicts (recommendation: use unique attributes like `id` or `key` instead)

## Update Cycle

- once per week, the GitHub Action discovers new plugins
- once per day, the GitHub Action updates the plugin versions

## Usage (Flakes)

Add the input to your `flake.nix`:

```nix
nix-jetbrains-plugins = {
  url = "github:PhilippHeuer/nix-jetbrains-plugins";
};
```

Then you can use the `addPlugins` function to add plugins to your IDE:

**Note**: You can search for plugins on the [Jetbrains Marketplace](https://plugins.jetbrains.com/). The number in the URL is the `id` of the plugin, e.g. `164` for `https://plugins.jetbrains.com/plugin/164-ideavim`.

```nix
{ pkgs, pkgs-unstable, inputs, ... }:

let
  pluginList = [
    # ai
    "17718" # github copilot

    # sast
    "7973" # sonarlint

    # hotkeys
    "164" # ideavim
    "9792" # key-promoter-x

    # themes
    "18682" # catppuccin-theme
    "23029" # catppuccin-icons

    # fun
    "8575" # nyan-progress-bar
  ];

  addPlugins = (inputs.nix-jetbrains-plugins.import pkgs-unstable).addPlugins;
  idea-community = addPlugins pkgs-unstable.jetbrains.idea-community-bin pluginList;
in {
  environment.systemPackages = [
    idea-community
  ];
}
```

## Credits / References

- https://github.com/NixOS/nixpkgs/tree/master/pkgs/applications/editors/jetbrains/plugins
- https://github.com/Cryolitia/nix-jetbrains-plugins

## License

Released under the [MIT License](./LICENSE).
