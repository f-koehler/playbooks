{
  pkgs ? import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/nixos-unstable.tar.gz") { },
}:

pkgs.mkShell {
  buildInputs = with pkgs; [
    ansible
    ansible-lint
    ansible-language-server
    yamllint
  ];

  shellHook = ''
    echo "Ansible development environment loaded!"
    echo "Available tools:"
    echo "- ansible: $(ansible --version | head -n1)"
    echo "- ansible-lint: $(ansible-lint --version)"
    echo "- ansible-language-server: $(ansible-language-server --version)"
    echo "- yamllint: $(yamllint --version)"
  '';
}
