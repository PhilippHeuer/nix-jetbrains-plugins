{ pkgs }:

let
  inherit (pkgs) lib fetchurl fetchzip;

  pluginsJson = builtins.fromJSON (builtins.readFile ./data/cache/plugins.json);

  fetchPluginSrc = plugin:
    let
      isJar = lib.hasSuffix ".jar" plugin.url;
      fetcher = if isJar then fetchurl else fetchzip;
    in
    fetcher {
      inherit (plugin) url hash;
      executable = isJar;
    };

in rec {
  byId = builtins.mapAttrs
    (id: plugin:
      ide: _:
      if !lib.elem ide plugin.compatible then
        throw "Plugin ${plugin.name} (${id}) does not support IDE ${ide}"
      else
        fetchPluginSrc plugin
    )
    pluginsJson;

  byKey = builtins.mapAttrs
    (id: plugin: byId.${id})
    pluginsJson;

  addPlugins = ide: ideBuild: unprocessedPlugins:
    let
      processPlugin = plugin:
        if byId ? "${plugin}" then byId."${plugin}" ide.pname null
        else if byKey ? "${plugin}" then byKey."${plugin}" ide.pname null
        else plugin;

      plugins = map processPlugin unprocessedPlugins;
      idePkg = ide.overrideAttrs (_: {
        disallowedReferences = [];
      });
    in
      pkgs.jetbrains.plugins.addPlugins idePkg plugins;
}
