#!/usr/bin/env python3
#-*- encoding=utf8 -*-

# GIMP Plug-in for the DDS file format
# Copyright (C) 2025 by Scriptkitz <scriptkitz@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

import os, sys, tempfile, zipfile
import xml.etree.ElementTree as ET

import re, subprocess, shutil


NESTED_STACK_END = object()

def conv_tga(filename, dest):
    try:
        args = [
            os.path.join(os.path.dirname(__file__), "texconv.exe"), 
            "-ft", "TGA", "-o", dest, filename
        ]
        subprocess.check_call(args, shell=True)
    except Exception as ex:
        Gimp.message("Error0: %s"%str(ex))
    
def check_bc6_bc7(filename):
    try:
        args = [
            os.path.join(os.path.dirname(__file__), "texdiag.exe"),
            "info", "-nologo",
            filename
        ]
        out = subprocess.check_output(args, shell=True).decode("utf-8")
        g = re.search("format = (\w*)", out)
        if g is not None:
            f = g.group(1)
            if f.startswith("BC6") or f.startswith("BC7"):
                return True
    except Exception as ex:
        Gimp.message("Error1: %s"%str(ex))
    return False

def load_dds(procedure, run_mode, file, metadata, flags, config, data):
    #if run_mode == Gimp.RunMode.INTERACTIVE:
    filename = file.peek_path()
    if not check_bc6_bc7(filename):
        builtin_proc = Gimp.get_pdb().lookup_procedure("file-dds-load")
        config = builtin_proc.create_config()
        config.set_property("file", file)
        config.set_property("run-mode", run_mode)
        return builtin_proc.run(config), flags
    fname = os.path.splitext(os.path.basename(filename))[0]
    tmp = tempfile.mkdtemp("-gimp-dds-load")
    try:
        conv_tga(filename, tmp)
        newfile = Gio.File.new_for_path(os.path.join(tmp, "%s.tga"%fname))
        builtin_proc = Gimp.get_pdb().lookup_procedure("file-tga-load")
        config = builtin_proc.create_config()
        config.set_property("run-mode", run_mode)
        config.set_property("file", newfile)
        return builtin_proc.run(config), flags
    except Exception as ex:
        Gimp.message("Exception:\n"+str(ex))
    finally:
        shutil.rmtree(tmp)

    return None
    
class FileDDSTexconv (Gimp.PlugIn):
    def do_set_i18n(self, procname):
        return False

    def do_query_procedures(self):
        return [ 'file-dds-texconv-load' ]

    def do_create_procedure(self, name):
        if name == 'file-dds-texconv-load':
            procedure = Gimp.LoadProcedure.new (self, name,
                                                Gimp.PDBProcType.PLUGIN,
                                                load_dds, None)
            procedure.set_menu_label("Load DDS (Texconv)")
            procedure.set_documentation ('load a DDS file with texconv.',
                                         'load a DDS file with texconv for GIMP3.',
                                         name)
            procedure.set_extensions ("dds")
            # procedure.add_boolean_argument(
            #     "sepAlpha", "sepAlpha", 
            #     "Load Alpha as Channel Instead of Transparency", 
            #     False, 
            #     GObject.ParamFlags.READWRITE)
        else:
            raise ValueError('Unknown procedure "%s"' % name)
        
        procedure.set_attribution('scriptkitz', #author
                                  'scriptkitz', #copyright
                                  '2025') #year
        return procedure


Gimp.main(FileDDSTexconv.__gtype__, sys.argv)
