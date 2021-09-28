#!/usr/bin/env python2
#-*- encoding=utf8 -*-

# GIMP Plug-in for the DDS file format
# Copyright (C) 2021 by Scriptkitz <scriptkitz@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

import re
import os.path
import shutil
import tempfile
import subprocess
from gimpfu import *


def run_smart(args):
    try:
        # argline = ' '.join(['"' + x + '"' for x in args])
        subprocess.check_call(args, shell=True)
    except Exception as ex:
        gimp_log("Error: %s"%str(ex))
    
def run_need(args):
    try:
        out = subprocess.check_output(args, shell=True)
        g = re.search("format = (\w*)", out)
        if g is not None:
            f = g.group(1)
            if f.startswith("BC6") or f.startswith("BC7"):
                return True
    except Exception as ex:
        gimp_log("Error: %s"%str(ex))
    return False

def load_dds_texconv( filename, raw_filename, no, bSepAlpha, bLoadMips, bFlipV):
    # gimp_log((filename, raw_filename, no, bSepAlpha, bLoadMips, bFlipV))
    BINARY = os.path.join(os.path.dirname(__file__), "texdiag.exe")
    if not run_need([BINARY, "info", "-nologo", filename.encode('gbk')]):
        return pdb['file-dds-load'](filename, raw_filename, bLoadMips, True)
    fname = os.path.splitext(os.path.basename(filename))[0]
    tmp = tempfile.mkdtemp("-gimp-dds-load")
    try:
        result = os.path.join(tmp, "%s.png"%fname)
        BINARY = os.path.join(os.path.dirname(__file__), "texconv.exe")
        run_smart([BINARY, "-ft", "PNG", "-o", tmp, filename.encode('gbk')])
        return pdb['file-png-load'](result, raw_filename)
    except Exception as ex:
        pdb.gimp_message("Exception:\n"+str(ex))
    finally:
        shutil.rmtree(tmp)
        # pass

    return None

def register_load_handlers():
    gimp.register_load_handler('file-dds-texconv-load', 'dds', '')
    # 注册mime处理句柄名,打开这类mime类型文件时候调用此处理句柄
    # pdb['gimp-register-file-handler-mime']('file-dds-texconv-load', 'image/vnd-ms.dds') 

def gimp_log(text):
    pdb.gimp_message(text)

register(
    'file-dds-texconv-load',
    'load a DDS file with texconv.',
    'load a DDS file with texconv.',
    'scriptkitz',
    'scriptkitz',
    '2021',
    'Label DDS',
    '*',
    [
        (PF_STRING, 'filename', 'The name of the file to load', ""),
        (PF_STRING, 'fawfilename', 'The name entered', ""),
        (PF_STRING, 'None', 'None', None), # 不知道为啥必须加这个，不然下面的选项就少一个
        (PF_TOGGLE, 'sepAlpha', 'Load Alpha as Channel Instead of Transparency', False),
        (PF_TOGGLE, 'loadMips', 'Load Mipmaps', False),
        (PF_TOGGLE, 'flipV', 'Flip Vertically', False)
    ],
    [(PF_IMAGE, 'image', 'Output image')], 
    load_dds_texconv,
    on_query=register_load_handlers,
    # menu="<Load>",
    menu='<Image>/File/OpenWith...'
)

main()