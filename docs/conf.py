#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# mpire documentation build configuration file, created by
# sphinx-quickstart on Tue Jun  27 15:35:20 2017.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

from datetime import datetime
import re

_version = '2.3.0'


def isBoostFunc(what, obj):
    return what == 'function' and obj.__repr__().startswith('<Boost.Python.function object at 0x')


def isBoostMethod(what, obj):
    """ I don't know how to distinguish boost and non-boost methods... """
    return what == 'method' and obj.__repr__().startswith('<unbound method ')


def isBoostStaticMethod(what, obj):
    return what == 'method' and obj.__repr__().startswith('<Boost.Python.function object at 0x')


def fixDocstring(app, what, name, obj, options, lines):
    if isBoostFunc(what, obj) or isBoostMethod(what, obj) or isBoostStaticMethod(what, obj):
        # Obtain formatted
        sig, l2 = boostFuncSignature(name, obj)

        # Formatted can contain empty parts at the beginning, remove those
        if len(l2) > 0 and l2[0] == "":
            l2 = l2[1:]

        # We must replace lines one by one (in-place) :-| (i.e., we cannot set lines = l2)
        # Knowing that l2 is always shorter than lines (l2 is docstring with the signature stripped off)
        for i in range(0, len(lines)):
            lines[i] = l2[i] if i < len(l2) else ''


def fixSignature(app, what, name, obj, options, signature, return_annotation):
    if what in ('attribute', 'class'):
        return signature, None

    if isBoostFunc(what, obj) or isBoostMethod(what, obj) or isBoostStaticMethod(what, obj):
        # Format. Note that second argument has to be None
        return boostFuncSignature(name, obj)[0], None


def replaceObjSelf(sig):
    # Split argument list only once on the comma. In the case that '(Obj)self' exists in the parameter list the first
    # part includes the '(Obj)self' part, the second part includes the remaining parameters. Due to optional parameters
    # there could be a '[' token in the '(Obj)self' part, which should be retained. Note that we only want to remove
    # the '(Obj)' part.
    try:
        ss = sig.split(',', 1)
        if ss[0].endswith('self') or ss[0].endswith('self ['):
            if ss[0].endswith('['):
                sig = '[' + ss[1]
            elif len(ss) > 1:
                sig = ss[1]
            else:
                sig = ""
        elif ' -> ' in ss[0]:
            sig = ') -> ' + ss[0].split(' -> ')[1]
    except IndexError:
        # grab the return value
        try:
            sig = ') -> ' + sig.split('->')[-1]
        except IndexError:
            sig = ')'
    return '(' + sig


def boostFuncSignature(name, obj):
    """
    Scan docstring of obj, returning tuple of properly formatted boost python signature
    (first line of the docstring) and the rest of docstring (as list of lines).
    The rest of docstring is stripped of 4 leading spaces which are automatically
    added by boost.
    """
    # Obtain the doc of this function, if it is None it is not a Boost method
    doc = obj.__doc__
    if doc is None:
        return None, None

    # Obtain the class name and function name
    cname = name.split('.')[1]
    nname = name.split('.')[-1]

    # The first line of the doc is always empty, so we remove it
    docc = doc.split('\n')
    if len(docc) < 2:
        return None, docc
    doc1 = docc[1]

    # Functions with weird docstring, likely not documented by boost
    if not re.match('^' + nname + r'(.*)->.*$', doc1):
        return None, docc

    # If doc1 ends with a ':' it means that there is a function description doc string following in the next part
    if doc1.endswith(':'):
        doc1 = doc1[:-1]
    strippedDoc = doc.split('\n')[2:]
    strippedDoc = [line.replace("->", "→") for line in strippedDoc]

    # Replace '(Obj)self' with 'self'
    sig = doc1.split('(', 1)[1]
    sig = replaceObjSelf(sig)

    # Fix doc string when overloaded functions are present. When there are overloaded function without description those
    # functions will not be displayed correctly, so we add a custom description to those
    new_strippedDoc = []
    has_description = False
    for line_nr, line in enumerate(strippedDoc):
        if line.startswith(nname):
            line = replaceObjSelf(line)
            new_strippedDoc.append(nname + line)
            if not has_description:
                new_strippedDoc.append("    Overloaded function without description")
        else:
            if len(line):
                has_description = True
            new_strippedDoc.append(line)

    # Fix signature of classes exposed with the vector_indexing_suite (the classes are named [...]Vector)
    if cname.endswith("Vector") and len(cname) > len("Vector"):
        if nname == "__contains__":
            sig = "( self, (object)arg) -> bool"
        if nname == "__delitem__":
            sig = "( self, (int)idx) -> None"
        if nname == "__getitem__":
            sig = "( self, (int)idx) -> object"
        if nname == "__setitem__":
            sig = "( self, (int)idx, (object)value) -> None"
        if nname == "append":
            sig = "( self, (object)value) -> None"
        if nname == "extend":
            sig = "( self, (object)list_of_values) -> None"

    # Fix signature of constructors, they do not return None
    if nname == "__init__":
        if sig.endswith("None"):
            sig = sig[:-4] + cname
        elif sig.endswith("None "):
            sig = sig[:-5] + cname
        new_strippedDoc = [line.replace("→ None", "→ %s" % cname) for line in new_strippedDoc]

    return sig, new_strippedDoc


def skipMember(app, what, name, obj, skip, options):
    # Skip some special methods
    if name.endswith('__getinitargs__') \
            or name.endswith('__instance_size__') \
            or name.endswith('__module__') \
            or name.endswith('__reduce__') \
            or name.endswith('__safe_for_unpickling__') \
            or name.endswith('__slots__') \
            or name.endswith('_enum.names') \
            or name.endswith('_enum.values') \
            or name.endswith('__getstate__') \
            or name.endswith('__setstate__') \
            or name.endswith('__getstate_manages_dict__') \
            or name.endswith('__doc__'):
        return True

    # Skip some enum class members
    if isinstance(obj, dict) and name in {"names", "values"}:
        return True

    return skip


def setup(app):
    # Register custom apps
    app.connect('autodoc-process-docstring', fixDocstring)
    app.connect('autodoc-process-signature', fixSignature)
    app.connect('autodoc-skip-member', skipMember)
    app.add_stylesheet('css/custom.css')


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx.ext.mathjax',
    'sphinx_autodoc_typehints',
    'sphinxcontrib.images'
]

# Add any paths that contain templates here, relative to this directory.
# templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The encoding of source files.
#
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'mpire'
copyright = '%d, Slimmer AI' % datetime.now().year
author = 'Slimmer AI'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.

version = _version
# The full version, including alpha/beta/rc tags.
release = _version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#
# today = ''
#
# Else, today_fmt is used as the format for a strftime call.
#
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#
# add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#
# show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
# keep_warnings = False

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'alabaster'
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = []

# The name for this set of Sphinx documents.
# "<project> v<release> documentation" by default.
#
# html_title = 'mpire v0.2.0'

# A shorter title for the navigation bar.  Default is the same as html_title.
#
# html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#
# html_logo = None

# The name of an image file (relative to this directory) to use as a favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#
# html_extra_path = []

# If not None, a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
# The empty string is equivalent to '%b %d, %Y'.
#
# html_last_updated_fmt = None

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#
# html_additional_pages = {}

# If false, no module index is generated.
#
# html_domain_indices = True

# If false, no index is generated.
#
# html_use_index = True

# If true, the index is split into individual pages for each letter.
#
# html_split_index = False

# If true, links to the reST sources are added to the pages.
#
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#
# html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#
# html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Language to be used for generating the HTML full-text search index.
# Sphinx supports the following languages:
#   'da', 'de', 'en', 'es', 'fi', 'fr', 'h', 'it', 'ja'
#   'nl', 'no', 'pt', 'ro', 'r', 'sv', 'tr', 'zh'
#
# html_search_language = 'en'

# A dictionary with options for the search language support, empty by default.
# 'ja' uses this config value.
# 'zh' user can custom change `jieba` dictionary path.
#
# html_search_options = {'type': 'default'}

# The name of a javascript file (relative to the configuration directory) that
# implements a search results scorer. If empty, the default will be used.
#
# html_search_scorer = 'scorer.js'

# Output file base name for HTML help builder.
htmlhelp_basename = 'mpiredoc'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
     # The paper size ('letterpaper' or 'a4paper').
     #
     # 'papersize': 'letterpaper',

     # The font size ('10pt', '11pt' or '12pt').
     #
     # 'pointsize': '10pt',

     # Additional stuff for the LaTeX preamble.
     #
     # 'preamble': '',

     # Latex figure (float) alignment
     #
     # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'mpire.tex', 'mpire Documentation',
     'Slimmer AI', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#
# latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#
# latex_use_parts = False

# If true, show page references after internal links.
#
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
#
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
#
# latex_appendices = []

# It false, will not define \strong, \code, 	itleref, \crossref ... but only
# \sphinxstrong, ..., \sphinxtitleref, ... To help avoid clash with user added
# packages.
#
# latex_keep_old_macro_names = True

# If false, no module index is generated.
#
# latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'mpire', 'mpire Documentation',
     [author], 1)
]

# If true, show URL addresses after external links.
#
# man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'mpire', 'mpire Documentation',
     author, 'mpire', 'A Python package for easy multiprocessing, but faster than multiprocessing.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#
# texinfo_appendices = []

# If false, no module index is generated.
#
# texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#
# texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#
# texinfo_no_detailmenu = False
