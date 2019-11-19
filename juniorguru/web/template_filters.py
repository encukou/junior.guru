from pathlib import Path

from jinja2 import Markup
from markdown import markdown
from markdown.extensions.toc import TocExtension

from . import app


@app.template_filter()
def email_link(email, text_template='{email}', classes=None):
    user, server = email.split('@')
    text = text_template.format(email=f'{user}&#64;<!---->{server}')
    classes = ' '.join(classes or [])
    class_attr = f' class="{classes}"' if classes else ''
    return Markup(
        f'<a href="mailto:{user}&#64;{server}"{class_attr}>{text}</a>'
    )


@app.template_filter()
def md(markdown_text, heading_level_base=1, heading_slug='heading'):
    toc = TocExtension(marker='',
                       baselevel=heading_level_base,
                       slugify=lambda value, separator: heading_slug)
    markup = markdown(markdown_text,
                      output_format='html5',
                      extensions=[toc])
    return Markup(markup)


REQUIREMENTS_MAPPING = {
    'mainstream programming language': 'základy programování',
    'databases': 'databáze',
    'data analysis': 'datová analýza',
    'servers and operations': 'správa serverů',
    'Linux and command line': 'Linux a příkazová řádka',
    'web backend': 'webový backend',
    'web frontend': 'webový frontend',
    'mobile apps development': 'mobilní aplikace',
    'mobile apps': 'mobilní aplikace',
}


@app.template_filter()
def job_requirement(requirement):
    try:
        return REQUIREMENTS_MAPPING[requirement]
    except KeyError:
        return requirement


TYPES_MAPPING = {
    'full-time': 'plný úvazek',
    'part-time': 'částečný úvazek',
    'paid-internship': 'placená stáž',
    'unpaid-internship': 'neplacená stáž',
    'volunteering': 'dobrovolnictví',
}


@app.template_filter()
def job_type(type_):
    try:
        return TYPES_MAPPING[type_]
    except KeyError:
        return type_
