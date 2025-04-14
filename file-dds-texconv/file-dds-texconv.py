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
            "-ft", "tga", "-o", dest, filename
        ]
        subprocess.check_call(args, shell=True)
    except Exception as ex:
        Gimp.message("Error0: %s"%str(ex))

def conv_dds(filename, dest, bMipmaps, bPow2):
    try:
        args = [
            os.path.join(os.path.dirname(__file__), "texconv.exe"), 
            "-ft", "dds", 
            "-f", "BC7_UNORM",
            "-y",
            "-o", dest, filename
        ]
        
        if bMipmaps:
            args.extend(["-m", "0"])
        else:
            args.extend(["-m", "1"])
        if bPow2:
            args.append("-pow2")
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

def export_dds(procedure, run_mode, image, file, options, metadata, config, data):
    if run_mode == Gimp.RunMode.INTERACTIVE:
        GimpUi.init(procedure.get_name())
        dialog = GimpUi.ProcedureDialog.new(procedure, config, "Export DDS...")
        dialog.fill(None)
        if not dialog.run():
            dialog.destroy()
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

        # dialog.destroy()
    Gimp.progress_init("Exporting dds image")
    o_filename = file.peek_path()
    fname = os.path.splitext(os.path.basename(o_filename))[0]
    tempdir = tempfile.mkdtemp('gimp-plugin-file-dds-texconv')
    tmp = os.path.join(tempdir, '%s.tga'%fname)

    pdb_proc   = Gimp.get_pdb().lookup_procedure('file-tga-export')
    pdb_config = pdb_proc.create_config()
    pdb_config.set_property('run-mode', Gimp.RunMode.NONINTERACTIVE)
    pdb_config.set_property('image', image)
    pdb_config.set_property('file', Gio.File.new_for_path(tmp))
    pdb_config.set_property('options', options)
    pdb_config.set_property('rle', False)
    pdb_config.set_property('origin', "top-left")
    pdb_proc.run(pdb_config)

    bMipmaps = config.get_property("bMipmaps")
    bPow2 = config.get_property("bPow2")
    conv_dds(tmp, os.path.dirname(o_filename), bMipmaps, bPow2)
    os.remove(tmp)
    Gimp.progress_end()

    return Gimp.ValueArray.new_from_values([
        GObject.Value(Gimp.PDBStatusType, Gimp.PDBStatusType.SUCCESS)
    ])

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
        return [ 'file-dds-texconv-export' ]

    def do_create_procedure(self, name):
        if name == 'file-dds-texconv-load':
            procedure = Gimp.LoadProcedure.new (self, name,
                                                Gimp.PDBProcType.PLUGIN,
                                                load_dds, None)
            procedure.set_documentation ('load a DDS file with texconv.',
                                         'load a DDS file with texconv for GIMP3.',
                                         name)
            procedure.set_extensions ("dds")
            # procedure.add_boolean_argument(
            #     "sepAlpha", "sepAlpha", 
            #     "Load Alpha as Channel Instead of Transparency", 
            #     False, 
            #     GObject.ParamFlags.READWRITE)
        elif name == 'file-dds-texconv-export':
            procedure = Gimp.ExportProcedure.new(self, name,
                                                 Gimp.PDBProcType.PLUGIN,
                                                 False, export_dds, None)
            procedure.set_image_types("*")
            procedure.set_menu_label('DDS (BC7)')
            procedure.set_documentation ('save an DDS file with texconv',
                                         'save an DDS file with texconv',
                                         name)
            procedure.set_extensions ("bc7.dds")
            procedure.add_boolean_argument(
                "bMipmaps", "Mipmaps",
                "Generate Mipmaps", 
                True, 
                GObject.ParamFlags.READWRITE)
            procedure.add_boolean_argument(
                "bPow2", "Fit power of 2",
                "Fit texture to power-of-2 for width and height.",
                False, 
                GObject.ParamFlags.READWRITE)
        else:
            raise ValueError('Unknown procedure "%s"' % name)
        
        procedure.set_attribution('scriptkitz', #author
                                  'scriptkitz', #copyright
                                  '2025') #year
        return procedure


Gimp.main(FileDDSTexconv.__gtype__, sys.argv)
