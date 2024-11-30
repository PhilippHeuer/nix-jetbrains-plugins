{
  description = "
    `JetBrains plugins as `Nix` expressions.
    Learn more in the flake [repo](https://github.com/PhilippHeuer/nix-jetbrains-plugins).
  ";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.11";
    nixos-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixos-master.url = "github:NixOS/nixpkgs/master";
  };

  outputs = {self, ... }:
    {
      import = pkgs: (import ./plugins.nix { inherit pkgs; });
    };
}
