{
  description = "JetBrains plugins as Nix expressions.";

  outputs =
    { self, ... }:
    {
      import = pkgs: (import ./plugins.nix { inherit pkgs; });
    };
}
