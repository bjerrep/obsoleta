#!/usr/bin/env python3
from package import Package
from log import inf, logger
from common import Setup
import glob, re, os, logging, sys, pathlib


def curly(a, b, first=False):
    if first:
        return '{"%s", "%s"}' % (a, b)
    return ',\n    {"%s", "%s"}' % (a, b)


def make_forward_decl(a, first=False):
    if first:
        return 'const char* obsoleta_entry_%s(const char*);' % a
    return '\nconst char* obsoleta_entry_%s(const char*);' % a


def make_entry(a, first=False):
    if first:
        return 'obsoleta_entry_%s' % a
    return ',\n    obsoleta_entry_%s' % a


def generate_c(package_or_path, src_dest, inc_dest):
    if isinstance(package_or_path, str):
        package = Package.construct_from_package_path(Setup('testdata/mini.conf'), package_or_path)
    else:
        package = package_or_path

    inf('c generator starting in %s' % package.get_path())

    template_src_inc_path = ('templates/c/src/*', 'templates/c/inc/*')
    name = package.get_name()
    version = package.get_version()
    try:
        c = package.get_value('language') == 'C'
    except:
        c = False

    name_version_list = curly(name, version, first=True)
    forward_decls = make_forward_decl(name, first=True)
    function_list = make_entry(name, first=True)

    if package.get_dependencies():
        for depends in package.get_dependencies():
            name_version_list += curly(depends.get_name(), depends.get_version())
            forward_decls += make_forward_decl(depends.get_name())
            function_list += make_entry(depends.get_name())

    for template_path, dest_path in zip(template_src_inc_path, (src_dest, inc_dest)):
        templates = glob.glob(template_path)

        for template in templates:
            if c and template.endswith('cpp.template'):
                continue
            template_name = os.path.basename(template)
            destfile = os.path.join(dest_path, os.path.splitext(template_name)[0])
            destfile = re.sub('name', name, destfile)
            inf('rewriting %s as %s' % (template_name, destfile))
            with open(template) as src:
                source = src.read()
                source = re.sub('#OBSOLETA_NAME#', name, source)
                source = re.sub('#OBSOLETA_NAME_VERSION_LIST#', name_version_list, source)
                source = re.sub('#OBSOLETA_FORWARD_DECL#', forward_decls, source)
                source = re.sub('#OBSOLETA_FUNCTION_LIST#', function_list, source)
                source = re.sub('#OBSOLETA_NOF_DEPENDS#', str(package.get_nof_dependencies()), source)

                pathlib.Path(os.path.abspath(dest_path)).mkdir(parents=True, exist_ok=True)
                with open(destfile, 'w') as dest:
                    dest.write(source)

    # in case the caller calls 'save' then save the generate history as well
    package.unmodified_dict["generate_c"] = {"autorefresh": "true", "rel_src": src_dest, "rel_inc": inc_dest}


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    generate_c(sys.argv[1], sys.argv[2], sys.argv[3])
