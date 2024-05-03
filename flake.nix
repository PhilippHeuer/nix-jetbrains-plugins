{
  description = "
    `JetBrains plugins as `Nix` expressions.
    Learn more in the flake [repo](https://github.com/PhilippHeuer/nix-jetbrains-plugins).
  ";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-23.11";
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    nixos-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = {self, ... }:
    {
      import = pkgs: (import ./plugins.nix { inherit pkgs; });
    };
}
