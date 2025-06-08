#!/usr/bin/env python
# encoding: utf-8
"""
git-chdiff

Created by Dan Weeks (dan [AT] danimal [DOT] org) on 2008-02-20.
Released to the Public Domain.
Refatorado em 2025 por Gabriel Izidoro, João Victor.
"""

import getopt
import os
import subprocess
import sys
import tempfile

import pwd
import getpass

HELP_MESSAGE = '''
git-chdiff <opts> [file1, file2, ...]

display diffs of git files using the chdiff utility 

  -h, --help        display this message
  -r, --revision    the revision of the file to use 
                       defaults to 'HEAD~1', the previous commit
  -w, --wait        cause chdiff to wait between files
  -v, --verbose     print more messages during operation
  --clean           clean any temp files that might have been left around
'''

TEMP_FILE_SUFFIX = '.temp'
TEMP_FILE_PREFIX = 'git-chdiff'
TEMP_DIRECTORY = '/var/tmp'

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def parse_arguments(argv):
    """
    Lê os argumentos passados via linha de comando e organiza em um dicionário.
    """
    try:
        # Define os argumentos válidos
        opts, args = getopt.getopt(argv[1:], 'hr:wv', ['clean', 'help', 'revision=', 'wait', 'verbose'])
    except getopt.error as msg:
        # Em caso de erro no argumento, levanta exceção
        raise Usage(msg)
    
    # Dicionário que armazena os valores das opções
    options = {
        'should_clean': False,     # Limpar arquivos temporários?
        'revision': 'HEAD~0',      # Revisão a ser usada no Git
        'wait': False,             # Esperar entre arquivos no chdiff
        'verbose': False,          # Mostrar mensagens adicionais?
        'file_names': []           # Lista de arquivos passados
    }

    # Processa cada opção capturada
    for option, value in opts:
        if option == '--clean':
            options['should_clean'] = True
        elif option in ('-h', '--help'):
            raise Usage(HELP_MESSAGE)
        elif option in ('-r', '--revision'):
            options['revision'] = value
        elif option in ('-w', '--wait'):
            options['wait'] = True
        elif option in ('-v', '--verbose'):
            options['verbose'] = True

    # Armazena os nomes dos arquivos no dicionário
    options['file_names'] = argv[1:]
    return options

def is_file_tracked_by_git(file_path):
    """
    Verifica se o arquivo está sendo rastreado (versionado) pelo Git.
    Retorna True se estiver, False caso contrário.
    """
    try:
        # Executa o comando git para verificar se o arquivo existe no repositório
        result = subprocess.run(['git', 'ls-files', '--error-unmatch', file_path],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        return result.returncode == 0
    except Exception:
        return False
    
def get_file_from_git_revision(revision, git_path):
    """
    Recupera o conteúdo de um arquivo em uma determinada revisão do Git.
    Retorna o conteúdo como string, ou None se falhar.
    """
    try:
        result = subprocess.run(['git', 'show', f'{revision}:{git_path}'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception:
        return None
    
def create_temp_file(content, verbose=False):
    """
    Cria um arquivo temporário com o conteúdo da revisão antiga.
    Retorna o caminho para o arquivo criado.
    """
    temp_file = tempfile.mkstemp(TEMP_FILE_SUFFIX, TEMP_FILE_PREFIX, TEMP_DIRECTORY)
    if verbose:
        print(f'    temp file: {temp_file[1]}')
    
    # Escreve o conteúdo no arquivo temporário
    with os.fdopen(temp_file[0], 'w') as temp_fp:
        temp_fp.write(content)

    return temp_file[1]

def run_chdiff(original_file, modified_file, wait=False):
    """
    Executa o comando chdiff para comparar dois arquivos.
    """
    # Se o modo "espera" estiver ativado, adiciona o argumento --wait
    wait_flag = '--wait' if wait else ''
    
    # Executa o comando com os arquivos passados
    subprocess.run(['chdiff', wait_flag, original_file, modified_file])

def main(argv=None):
    # Se nenhum argumento for passado, usa os da linha de comando
    if argv is None:
        argv = sys.argv

    try:
        # Faz o parsing (leitura) dos argumentos da linha de comando
        options = parse_arguments(argv)
    except Usage as err:
        # Se houver erro nos argumentos, mostra mensagem de uso
        print(f"{sys.argv[0].split('/')[-1]}: {err.msg}", file=sys.stderr)
        print(HELP_MESSAGE, file=sys.stderr)
        return 2

    # Se o usuário pediu para limpar os arquivos temporários
    if options['should_clean']:
        return clean_temp_files(options['verbose'])

    # Para cada arquivo passado como argumento
    for file_name in options['file_names']:
        # Normaliza o caminho do arquivo (ex: ./arquivo.py → /caminho/absoluto/arquivo.py)
        normalized_file = os.path.normpath(file_name)
        git_path = normalized_file

        if options['verbose']:
            print(f'-> working on {normalized_file}')

        # Verifica se o arquivo existe localmente
        if not os.path.isfile(normalized_file):
            print(f'{normalized_file} is not a file')
            continue

        # Verifica se o arquivo está versionado no Git
        if not is_file_tracked_by_git(normalized_file):
            print(f'{normalized_file} not in git repository.....skipping')
            continue

        # Tenta recuperar o conteúdo do arquivo na revisão anterior (ex: HEAD~0)
        file_content = get_file_from_git_revision(options['revision'], git_path)
        if not file_content:
            print(f'problem getting revision {options["revision"]} of file {normalized_file}')
            continue

        # Cria um arquivo temporário com o conteúdo da revisão antiga
        temp_file_path = create_temp_file(file_content, verbose=options['verbose'])

        # Roda o chdiff para comparar o arquivo atual com o da revisão antiga
        run_chdiff(temp_file_path, normalized_file, wait=options['wait'])

        # Se o modo espera estiver ativado, remove o arquivo temporário após uso
        if options['wait']:
            os.unlink(temp_file_path)
            
def clean_temp_files(verbose=False):
    """
    Como nem sempre esperamos pelo comando chdiff, nem sempre podemos limpar
    os arquivos temporários que criamos. Isso apagará todos os arquivos temporários
    do git-chdiff que possuímos.
    """

    try:
        if verbose:
            print('scanning for git-chdiff temp files to clean')
        my_uid = pwd.getpwnam(getpass.getuser())[2]
        files_in_tmp = os.listdir(TEMP_DIRECTORY)
        for file_name in files_in_tmp:
            normalized_file = os.path.join(TEMP_DIRECTORY, file_name)
            # pula diretórios
            if not os.path.isfile(normalized_file):
                continue
            # pula qualquer coisa que não esteja nomeada corretamente
            if not file_name.startswith(TEMP_FILE_PREFIX):
                continue
            # pula se não for nosso arquivo
            if os.stat(normalized_file)[4] != my_uid:
                continue
            # se estivermos aqui, somos donos do arquivo e ele está nomeado corretamente
            # remova-o
            if verbose:
                print('removing temp file: %s' % normalized_file)
            os.unlink(normalized_file)
        return 0
    except Exception as e:
        if verbose:
            print('Clean failed:', e, file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
