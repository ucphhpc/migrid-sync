#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridscriptgen - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
# 
# This file is part of MiG.
# 
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#


"""Generate MiG vgrid scripts for the speficied programming languages. Called without arguments the generator creates scripts for all supported languages. If one or more languages are supplied as arguments, only those languages will be generated.
"""

# Generator version (automagically updated by cvs)
__version__ = "$Revision: 2590 $"
# $Id: vgridscriptgen.py 2590 2009-02-25 10:45:03Z jones $

from publicscriptgen import *


#######################################
# Script generator specific functions #
#######################################
# Generator usage
def usage():
    print "Usage: vgridscriptgen.py OPTIONS [LANGUAGE ... ]"
    print "Where OPTIONS include:"
    print " -c CURL_CMD\t: Use curl from CURL_CMD"
    print " -h\t\t: Print this help"
    print " -p PYTHON_CMD\t: Use PYTHON_CMD as python interpreter"
    print " -s SH_CMD\t: Use SH_CMD as sh interpreter"
    print " -v\t\t: Verbose output"
    print " -V\t\t: Show version"
# end usage

def version():
    print "MiG VGrid Script Generator: %s" % (__version__)
# end version

def version_function(lang):
    s = ""
    s += begin_function(lang, "version", [])
    if lang == "sh":
        s += "\techo \"MiG VGrid Scripts: %s\"\n" % (__version__)
    elif lang == "python":
        s += "\tprint \"MiG VGrid Scripts: %s\"\n" % (__version__)
    s += end_function(lang, "version")

    return s
# end version_function


###########################
# Script helper functions #
###########################
def vgrid_single_argument_usage_function(lang, extension, op, first_arg):
    # Extract op from function name
    #op = sys._getframe().f_code.co_name.replace("_usage_function","")

    usage_str = "Usage: %s%s.%s [OPTIONS] %s" % (mig_prefix, op, extension, first_arg)
    s = ""
    s += begin_function(lang, "usage", [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, "usage")
    
    return s
# end vgrid_single_argument_usage_function

def vgrid_two_arguments_usage_function(lang, extension, op, first_arg, second_arg):
    # Extract op from function name
    #op = sys._getframe().f_code.co_name.replace("_usage_function","")

    usage_str = "Usage: %s%s.%s [OPTIONS] %s %s" % (mig_prefix, op, extension, first_arg, second_arg)
    s = ""
    s += begin_function(lang, "usage", [])
    s += basic_usage_options(usage_str, lang)
    s += end_function(lang, "usage")
    
    return s
# end vgrid_two_arguments_usage_function


###########################
# Communication functions #
###########################

def vgrid_single_argument_function(lang, curl_cmd, command, first_arg, curl_flags = ""):
    s = ""
    s += begin_function(lang, "submit_command", [first_arg])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    if lang == "sh":
        s += """
        curl=\"%s %s\"""" % (curl_cmd, curl_flags)
        s += """
        $curl \\
                --fail \\
                --cert $cert_file \\
                --key $key_file \\
                $ca_check \\
                $password_check \\
                --url \"$mig_server/cgi-bin/%s.py?%s=$%s;output_format=txt\" 
""" % (command, first_arg, first_arg)
    elif lang == "python":
        s += """
        curl = \"%s %s\"""" % (curl_cmd, curl_flags)
	
	# TODO: create valid python code
	#        s += """
	#        status = os.system("%%s --fail --cert %%s --key %%s %%s %%s --url '%%s/cgi-bin/%s.py?%s=$%s&%s=$%s;output_format=txt;with_html=false'" % (curl, cert_file, key_file, ca_check, password_check, mig_server)) 
	#        return status >> 8
	#""" % (command, first_arg, first_arg, second_arg, second_arg, second_arg)
    else:
        print "Error: %s not supported!" % (lang)
        return ""

    s += end_function(lang, "submit_command")
    return s

def vgrid_single_argument_upload_function(lang, curl_cmd, command, content_type, first_arg, curl_flags = ""):
    s = ""
    s += begin_function(lang, "submit_command", [first_arg])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    if lang == "sh":
        s += """
        curl=\"%s %s\"""" % (curl_cmd, curl_flags)
        s += """
        $curl \\
	        -H "Content-Type: %s" \\
                --fail \\
                --cert $cert_file \\
                --key $key_file \\
                $ca_check \\
                $password_check \\
		--upload-file $%s \\
                --url \"$mig_server\" 
""" % (content_type, first_arg)
    elif lang == "python":
        s += """
        curl = \"%s %s\"""" % (curl_cmd, curl_flags)
	
	# TODO: create valid python code
	#        s += """
	#        status = os.system("%%s --fail --cert %%s --key %%s %%s %%s --url '%%s/cgi-bin/%s.py?%s=$%s&%s=$%s;output_format=txt;with_html=false'" % (curl, cert_file, key_file, ca_check, password_check, mig_server)) 
	#        return status >> 8
	#""" % (command, first_arg, first_arg, second_arg, second_arg, second_arg)
    else:
        print "Error: %s not supported!" % (lang)
        return ""

    s += end_function(lang, "submit_command")
    return s

def vgrid_two_arguments_function(lang, curl_cmd, command, first_arg, second_arg, curl_flags = ""):
    s = ""
    s += begin_function(lang, "submit_command", [first_arg, second_arg])
    s += ca_check_init(lang)
    s += password_check_init(lang)
    if lang == "sh":
        s += """
        curl=\"%s %s\"""" % (curl_cmd, curl_flags)
        s += """
        $curl \\
                --fail \\
                --cert $cert_file \\
                --key $key_file \\
                $ca_check \\
                $password_check \\
                --url \"$mig_server/cgi-bin/%s.py?%s=$%s&%s=$%s;output_format=txt\" 
""" % (command, first_arg, first_arg, second_arg, second_arg)
    elif lang == "python":
        s += """
        curl = \"%s %s\"""" % (curl_cmd, curl_flags)
	
	# TODO: create valid python code
	#        s += """
	#        status = os.system("%%s --fail --cert %%s --key %%s %%s %%s --url '%%s/cgi-bin/%s.py?%s=$%s&%s=$%s;output_format=txt;with_html=false'" % (curl, cert_file, key_file, ca_check, password_check, mig_server)) 
	#        return status >> 8
	#""" % (command, first_arg, first_arg, second_arg, second_arg, second_arg)
    else:
        print "Error: %s not supported!" % (lang)
        return ""

    s += end_function(lang, "submit_command")
    return s



########################
# Main part of scripts #
########################

def vgrid_single_argument_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """
    
    s = ""
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 1, 1)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':        
        s += """

first_arg="$1"

submit_command $first_arg
"""
    elif lang == "python":
        s += """
first_arg = sys.argv[1]

submit_command(first_arg)
"""
    else:
        print "Error: %s not supported!" % (lang)

    return s

def vgrid_two_arguments_main(lang):
    """
    Generate main part of corresponding scripts.

    lang specifies which script language to generate in.
    """
    
    s = ""
    s += basic_main_init(lang)
    s += parse_options(lang, None, None)
    s += arg_count_check(lang, 2, 2)
    s += check_conf_readable(lang)
    s += configure(lang)
    if lang == 'sh':        
        s += """

first_arg="$1"
second_arg="$2"

submit_command $first_arg $second_arg
"""
    elif lang == "python":
        s += """
first_arg = sys.argv[1]
second_arg = sys.argv[2]

submit_command(first_arg, second_arg)
"""
    else:
        print "Error: %s not supported!" % (lang)

    return s

#######################
# Generator functions #
#######################

def generate_single_argument(op, first_arg, scripts_languages, dest_dir="."):
    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("generate_","")
    curl_flags = ""
    # Generate op script for each of the languages in scripts_languages
    for lang, interpreter, extension in scripts_languages:
        verbose(verbose_mode, "Generating %s script for %s" % (op, lang))
        script_name = "%s%s.%s" % (mig_prefix, op, extension)

        script = ""
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        
        script += vgrid_single_argument_usage_function(lang, extension, op, first_arg)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += vgrid_single_argument_function(lang, curl_cmd, op, first_arg, curl_flags = "")
        script += vgrid_single_argument_main(lang)

        write_script(script, dest_dir + os.sep + script_name)
        
    return True

def generate_single_argument_upload(op, content_type, first_arg, scripts_languages, dest_dir="."):
    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("generate_","")
    curl_flags = ""
    # Generate op script for each of the languages in scripts_languages
    for lang, interpreter, extension in scripts_languages:
        verbose(verbose_mode, "Generating %s script for %s" % (op, lang))
        script_name = "%s%s.%s" % (mig_prefix, op, extension)

        script = ""
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        
        script += vgrid_single_argument_usage_function(lang, extension, op, first_arg)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += vgrid_single_argument_upload_function(lang, curl_cmd, op, content_type, first_arg, curl_flags = "")
        script += vgrid_single_argument_main(lang)

        write_script(script, dest_dir + os.sep + script_name)
        
    return True

def generate_two_arguments(op, first_arg, second_arg, scripts_languages, dest_dir="."):
    # Extract op from function name
    # op = sys._getframe().f_code.co_name.replace("generate_","")
    
    curl_flags = ""
    # Generate op script for each of the languages in scripts_languages
    for lang, interpreter, extension in scripts_languages:
        verbose(verbose_mode, "Generating %s script for %s" % (op, lang))
        script_name = "%s%s.%s" % (mig_prefix, op, extension)

        script = ""
        script += init_script(op, lang, interpreter)
        script += version_function(lang)
        
        script += vgrid_two_arguments_usage_function(lang, extension, op, first_arg, second_arg)
        script += check_var_function(lang)
        script += read_conf_function(lang)
        script += vgrid_two_arguments_function(lang, curl_cmd, op, first_arg, second_arg, curl_flags = "")
        script += vgrid_two_arguments_main(lang)

        write_script(script, dest_dir + os.sep + script_name)
        
    return True

############
### Main ###
############

# Defaults
verbose_mode = False
test_script = False

# Supported MiG operations (don't add 'test' as it is optional)

script_ops_two_args = []
# Vgrid functions
script_ops_two_args.append(["addvgridmember", "new_member", "vgrid_name"])
script_ops_two_args.append(["addvgridowner", "new_owner", "vgrid_name"])
script_ops_two_args.append(["addvgridres", "new_resource", "vgrid_name"])
script_ops_two_args.append(["rmvgridmember", "remove_member", "vgrid_name"])
script_ops_two_args.append(["rmvgridowner", "remove_owner", "vgrid_name"])
script_ops_two_args.append(["rmvgridres", "remove_resource", "vgrid_name"])
# Res functions
script_ops_two_args.append(["addresowner", "unique_resource_name", "cert_name"])
script_ops_two_args.append(["rmresowner", "unique_resource_name", "cert_name"])

script_ops_two_args.append(["startexe", "unique_resource_name", "exe_name"])
script_ops_two_args.append(["statusexe", "unique_resource_name", "exe_name"])
script_ops_two_args.append(["stopexe", "unique_resource_name", "exe_name"])
script_ops_two_args.append(["restartexe", "unique_resource_name", "exe_name"])
#script_ops_two_args.append(["resetexe", "unique_resource_name", "exe_name"])
script_ops_two_args.append(["startallexes", "unique_resource_name", "all"])
script_ops_two_args.append(["statusallexes", "unique_resource_name", "all"])
script_ops_two_args.append(["stopallexes", "unique_resource_name", "all"])
script_ops_two_args.append(["restartallexes", "unique_resource_name", "all"])


script_ops_single_arg = []
# Vgrid functions
script_ops_single_arg.append(["createvgrid", "vgrid_name"])
script_ops_single_arg.append(["lsvgridmembers", "vgrid_name"])
script_ops_single_arg.append(["lsvgridowners", "vgrid_name"])
script_ops_single_arg.append(["lsvgridres", "vgrid_name"])
# Res functions
script_ops_single_arg.append(["lsresowners", "unique_resource_name"])

script_ops_single_arg.append(["startfe", "unique_resource_name"])
script_ops_single_arg.append(["statusfe", "unique_resource_name"])
script_ops_single_arg.append(["stopfe", "unique_resource_name"])

# action_allexes scripts obsolete, use actionexe all=true instead
#script_ops_single_arg.append(["startallexes", "unique_resource_name"])
#script_ops_single_arg.append(["statusallexes", "unique_resource_name"])
#script_ops_single_arg.append(["stopallexes", "unique_resource_name"])
#script_ops_single_arg.append(["restartallexes", "unique_resource_name"])
#script_ops_single_arg.append(["resetallexes", "unique_resource_name"])

script_ops_single_upload_arg = []
script_ops_single_upload_arg.append(["submitresconf", "text/resourceconf", "configuration_file"])
script_ops_single_upload_arg.append(["submitnewre", "text/runtimeenvconf", "configuration_file"])

# Script prefix for all user scripts
mig_prefix = "mig"

# Default commands:
sh_lang = "sh"
# Disable globbing with the '-f' flag
sh_cmd = "/bin/sh -f"
sh_ext = "sh"
python_lang = "python"
python_cmd = "/usr/bin/python"
python_ext = "py"
curl_cmd = "/usr/bin/curl"
dest_dir = "."

# Only run interactive commands if called directly as executable
if __name__ == '__main__':
    opts_str = "c:d:hp:s:tvV"
    try:
        opts, args = getopt.getopt(sys.argv[1:], opts_str)
    except getopt.GetoptError, e:
        print "Error: ", e.msg
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == "-c":
            curl_cmd = val
        elif opt == "-d":
            dest_dir = val
        elif opt == "-p":
            python_cmd = val
        elif opt == "-s":
            sh_cmd = val
        elif opt == "-t":
            test_script = True
        elif opt == "-v":
            verbose_mode = True
        elif opt == "-V":
            version()
            sys.exit(0)
        elif opt == "-h":
            usage()
            sys.exit(0)
        else:
            print "Error: %s not supported!" % (opt)
            usage()
            sys.exit(1)

    verbose(verbose_mode, "using curl from: %s" % curl_cmd)
    verbose(verbose_mode, "using sh from: %s" % sh_cmd)
    verbose(verbose_mode, "using python from: %s" % python_cmd)
    verbose(verbose_mode, "writing script to: %s" % dest_dir)

    if not os.path.isdir(dest_dir):
        print "Error: destination directory doesn't exist!"
        sys.exit(1)

    argc = len(args)
    if argc == 0:
        # Add new languages here
        languages = [(sh_lang, sh_cmd, sh_ext),
                     (python_lang, python_cmd, python_ext)]
        for lang, cmd, ext in languages:
            print "Generating %s scripts" % lang
    else:
        languages = []
        # check arguments
        for lang in args:
            if lang == "sh":
                interpreter = sh_cmd
                extension = sh_ext
            elif lang == "python":
                interpreter = python_cmd
                extension = python_ext
            else:
                print "Unknown script language: %s - ignoring!" % (lang)
                continue

            print "Generating %s scripts" % lang

            languages.append((lang, interpreter, extension))

    # Generate all scripts
    for op in script_ops_single_arg:
        generate_single_argument(op[0], op[1], languages, dest_dir)

    for op in script_ops_single_upload_arg:
        generate_single_argument_upload(op[0], op[1], languages, dest_dir)

    for op in script_ops_two_args:
        generate_two_arguments(op[0], op[1], op[2], languages, dest_dir)

    # if test_script:
    #    generate_test(languages)

    sys.exit(0)
