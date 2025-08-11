{ pkgs }:

let
  inherit (pkgs) lib fetchurl fetchzip;

  pluginsJson = builtins.fromJSON (builtins.readFile ./data/cache/plugins-latest.json);
  fetchPluginSrc = url: hash:
    let
      isJar = lib.hasSuffix ".jar" url;
      fetcher = if isJar then fetchurl else fetchzip;
    in
    fetcher {
      executable = isJar;
      inherit url hash;
    };
  files = builtins.mapAttrs (key: value: fetchPluginSrc key value) pluginsJson.files;
  ids = builtins.attrNames pluginsJson.plugins;
in rec {
  mkPlugin = id: file: files."${file}";

  selectFile = id: ide: build:
  let
    plugin = pluginsJson.plugins."${id}";
    availableBuilds = builtins.attrNames plugin.builds;
    buildNo = if build == "latest" then
      builtins.elemAt availableBuilds (builtins.length availableBuilds - 1)
    else
      build;
  in
    if !builtins.elem ide pluginsJson.plugins."${id}".compatible then
      throw "Plugin with id ${id} does not support IDE ${ide}"
    else if !pluginsJson.plugins."${id}".builds ? "${buildNo}" then
      throw "Plugin with id ${id} does not support build ${buildNo}"
    else if pluginsJson.plugins."${id}".builds."${buildNo}" == null then
      throw "Plugin with id ${id} does not support build ${buildNo}"
    else
      pluginsJson.plugins."${id}".builds."${buildNo}";

  byId = builtins.listToAttrs
    (map
      (id: {
        name = id;
        value = ide: build: mkPlugin id (selectFile id ide build);
      })
      ids);

  byKey = builtins.listToAttrs
    (map
      (id: {
        name = pluginsJson.plugins."${id}".key;
        value = byId."${id}";
      })
      ids);

  addPlugins = ide: ideBuild: unprocessedPlugins:
    let
      buildNo = if ideBuild != null then ideBuild else ide.buildNumber;
      processPlugin = plugin:
        if byId ? "${plugin}" then byId."${plugin}" ide.pname buildNo else
        if byKey ? "${plugin}" then byKey."${plugin}" ide.pname buildNo else
        plugin;

      plugins = map processPlugin unprocessedPlugins;
      idePkg = ide.overrideAttrs (_: {
        disallowedReferences = []; # <- fix the impurity problem
      });

    in pkgs.jetbrains.plugins.addPlugins idePkg plugins;
}
