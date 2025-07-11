{
  inputs = {
    # nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/default";
  };

  outputs =
    { systems, nixpkgs, ... }@inputs:
    let
      eachSystem = f: nixpkgs.lib.genAttrs (import systems) (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = eachSystem (pkgs: {
        default = pkgs.mkShell {
          buildInputs = [
            pkgs.kubectl
            pkgs.kind
            pkgs.k9s
            pkgs.uv
            pkgs.yq-go
            pkgs.gitleaks
            pkgs.pre-commit
            pkgs.cmctl
          ];

          shellHook = ''
            export SHELL=${pkgs.zsh}/bin/zsh
            exec $SHELL
          '';

        };
      });
    };
}
