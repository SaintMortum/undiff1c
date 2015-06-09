#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import logging
import os
import platform
import re
import subprocess
import shutil
import sys
import tempfile
from unidiff import PatchSet

__version__ = '0.0.1'

logging.basicConfig(level=logging.INFO)  # DEBUG => print ALL msgs
log = logging.getLogger('undiff1c')

modified = re.compile('^(?:M|A)(\s+)(?P<name>.*)')


def get_config_param(param):
    """
    Parse config file and find source dir in it
    """
    curdir = os.curdir
    if '__file__' in globals():
        curdir = os.path.dirname(os.path.abspath(__file__))

    config = None
    for loc in curdir, os.curdir, os.path.expanduser('~'):
        try:
            with open(os.path.join(loc, 'precommit1c.ini')) as source:
                if sys.version_info < (3, 0, 0):
                    from ConfigParser import ConfigParser  # @NoMove @UnusedImport
                else:
                    from configparser import ConfigParser

                config = ConfigParser()
                config.read_file(source)
                break
        except IOError:
            pass

    if config is not None and config.has_option('default', param):
        value = config.get('default', param)
        return value

    return None

def get_list_of_comitted_files():
    """
    Return the list of files to be decompiled
    """
    files = []
    output = []
    try:
        output = subprocess.check_output(['git', 'diff-index', '--name-status', '--cached', 'HEAD']).decode('utf-8')
    except subprocess.CalledProcessError:
        try:
            output = subprocess.check_output(['git', 'status', '--porcelain']).decode('utf-8')
        except subprocess.CalledProcessError:
            print('Error diff files get')
            return files

    for result in output.split('\n'):
        logging.info(result)
        if result != '':
            match = modified.match(result)
            if match:
                files.append(match.group('name'))

    return files

def get_diff_forfile(file):
    tmppath = tempfile.mktemp()
    command = ['git', 'diff', 'HEAD', file]
    logging.debug("{}".format(command))
    print("{}".format(command))
    try:
        output = subprocess.check_output(command).decode('utf-8')
    except subprocess.CalledProcessError:
        logging.error('Error diff files {}'.format(file))
        return None
    with open(tmppath, 'w') as f:
        f.write(output)
    #print("{}".format(output))
    return tmppath

    
def git_reset_file(file, sha):
    output = subprocess.check_output(['git', 'reset', sha, file]).decode('utf-8')


def main():
    parser = argparse.ArgumentParser(description='Утилита для проверки ошибочно изменных файлов в индексе')
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(__version__))
    parser.add_argument('-v', '--verbose', dest='verbose_count', action='count', default=0,
                        help='Increases log verbosity for each occurence.')
    parser.add_argument('--g', action='store_true', default=False,
                        help='Запустить чтение индекса из git и определить список файлов для разбора')
    
    args = parser.parse_args()

    log.setLevel(10)#max(3 - args.verbose_count, 0) * 10)
    taglistchange = ('<d3p1:id>', '<d3p1:fullIntervalBegin>', '<d3p1:fullIntervalEnd>', '<d3p1:visualBegin>')

    if args.g is True:
        files = get_list_of_comitted_files()
        
        for file in files:
            if not file[-12:] == "Template.xml":
                continue
                
            data = get_diff_forfile(file)
            if data is None:
                logging.error("diff file not exists {}".forma(file))
                continue
            pathc = PatchSet.from_filename(data, encoding='utf-8')
            print(data)
            print(pathc.modified_files)
            for f in pathc.modified_files:
                logging.debug('file is {}'.format(f))
                modifiedsource, modifiedtarget = [],[]
                for hunk in f:
                    modifiedsource = modifiedsource + list(filter(lambda x: not x[:1] == " ", hunk.source))
                    modifiedtarget = modifiedtarget + list(filter(lambda x: not x[:1] == " ", hunk.target))
                
                sourcetags = list(filter(lambda x: x[1:].strip().startswith(taglistchange), modifiedsource))
                targettags = list(filter(lambda x: x[1:].strip().startswith(taglistchange), modifiedtarget))
                
                if not (len(sourcetags) == len(modifiedsource) and \
                    len(targettags) == len(modifiedtarget) and \
                    len(sourcetags) == len(targettags)):
                    continue
            
                #Теперь надо будет отменить изменения в индексе для файла. 
                git_reset_file(file, 'HEAD')
                break
    

if __name__ == '__main__':
    sys.exit(main())

