#!/usr/bin/env python
# encoding: utf-8
"""
git-external-chdiff

Created by Dan Weeks (dan [AT] danimal [DOT] org) on 2008-02-27.
Refatorado em 2025 por [Seu Nome]
"""

import sys
import subprocess
import os

def parse_external_diff_args(argv):
    """
    Extrai os caminhos dos arquivos antigo e novo a partir dos argumentos
    passados automaticamente pelo Git (via GIT_EXTERNAL_DIFF).

    Git envia os seguintes argumentos:
    argv[0] - script
    argv[1] - caminho do repositório
    argv[2] - arquivo original (na revisão antiga)
    argv[3] - número SHA antigo
    argv[4] - caminho do repositório
    argv[5] - arquivo modificado (no estado atual)
    argv[6] - número SHA novo
    """
    try:
        old_file = argv[2]
        new_file = argv[5]
        return old_file, new_file
    except IndexError:
        print("Erro: argumentos insuficientes fornecidos pelo Git.", file=sys.stderr)
        sys.exit(1)

def run_chdiff(old_file, new_file, wait=True, verbose=False):
    """
    Executa o utilitário chdiff para comparar dois arquivos.
    """
    wait_flag = '--wait' if wait else ''
    command = ['chdiff', wait_flag, old_file, new_file]

    if verbose:
        print(f'Executando: {" ".join(command)}')

    try:
        subprocess.run(command, env=os.environ)
    except FileNotFoundError:
        print("Erro: 'chdiff' não encontrado no sistema.", file=sys.stderr)
        sys.exit(1)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    old_file, new_file = parse_external_diff_args(argv)
    run_chdiff(old_file, new_file, wait=True, verbose=False)

if __name__ == '__main__':
    main()