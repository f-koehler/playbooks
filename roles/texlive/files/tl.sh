#!/bin/bash

cd /tmp
mkdir texlive
cd texlive
mkdir tl-installer
wget http://ftp.cstug.cz/pub/tex/local/tlpretest/install-tl-unx.tar.gz
tar xzf install-tl-unx.tar.gz --strip-components=1 -C tl-installer
cd tl-installer

cat > minimal.profile << EOF
selected_scheme scheme-minimal
binary_x86_64-linux 1
collection-basic 1
in_place 0
option_adjustrepo 1
option_autobackup 1
option_backupdir tlpkg/backups
option_desktop_integration 0
option_doc 0
option_file_assocs 0
option_fmt 1
option_letter 0
option_menu_integration 0
option_path 0
option_post_code 1
option_src 1
option_sys_bin /usr/local/bin
option_sys_info /usr/local/share/info
option_sys_man /usr/local/share/man
option_w32_multi_user 0
option_write18_restricted 1
portable 0
EOF

./install-tl -repository http://ftp.cstug.cz/pub/tex/local/tlpretest/ -profile minimal.profile

rm -rf /tmp/texlive
