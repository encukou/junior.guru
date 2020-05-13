import json
from pathlib import Path
from textwrap import dedent

import pytest
from lxml import html
from strictyaml import Enum, Map, Optional, Seq, Str, Url, load

from juniorguru.scrapers.pipelines import sections_parser
from juniorguru.scrapers.pipelines.sections_parser import (ListSection,
                                                           TextFragment)


schema = Seq(
    Map({
        Optional('heading'): Str(),
        'type': Enum(['paragraph', 'list']),
        'contents': Seq(Str()),
    })
)


def generate_sections_parser_params(fixtures_dir):
    for html_path in (Path(__file__).parent / fixtures_dir).rglob('*.html'):
        yaml_path = html_path.with_suffix('.yml')
        if yaml_path.is_file():
            yaml = load(yaml_path.read_text(), schema)
            # use json.loads/json.dumps to recursively convert all
            # ordered dicts to dicts, which significantly improves readability
            # of the pytest diff
            expected = json.loads(json.dumps(yaml.data))
            yield pytest.param(html_path.read_text(), expected,
                               id=html_path.name)  # better readability
        else:
            yield pytest.param('', '',
                               id=html_path.name,  # better readability
                               marks=pytest.mark.skip)


@pytest.mark.parametrize('description_raw,expected',
                         generate_sections_parser_params('fixtures_sections_parser'))
def test_sections_parser(item, spider, description_raw, expected):
    item['description_raw'] = description_raw
    item = sections_parser.Pipeline().process_item(item, spider)

    assert item['sections'] == expected


def test_intersperse():
    assert sections_parser.intersperse([1, 2, 3], 42) == [1, 42, 2, 42, 3]


def test_section_to_re():
    section = ListSection(heading='Who are you?', contents=[
        'You are a native German speaker',
        'You love self-management',
    ])

    assert sections_parser.section_to_re(section).pattern == (
        r'\s*'
        r'Who\ are\ you\?'
        r'\s+'
        r'(?:\W{1,2} )?You\ are\ a\ native\ German\ speaker'
        r'\s+'
        r'(?:\W{1,2} )?You\ love\ self\-management'
        r'\s*'
    )


def test_section_to_re_no_heading():
    section = ListSection(heading='', contents=[
        'You are a native German speaker',
        'You love self-management',
    ])

    assert sections_parser.section_to_re(section).pattern == (
        r'\s*'
        r'(?:\W{1,2} )?You\ are\ a\ native\ German\ speaker'
        r'\s+'
        r'(?:\W{1,2} )?You\ love\ self\-management'
        r'\s*'
    )


@pytest.mark.parametrize('section', [
    ListSection(heading='Who are you?', contents=[]),
    ListSection(heading='', contents=[])
])
def test_section_to_re_no_contents(section):
    with pytest.raises(ValueError):
        sections_parser.section_to_re(section)


def test_split_by_section():
    text_fragment = TextFragment(dedent('''
        Text before the list section 💖

        Who are you?

        You are a native German speaker
        You love self-management and can use common sense

        Text after the list section 🛠
    '''))
    section = ListSection(heading='Who are you?', contents=[
        'You are a native German speaker',
        'You love self-management and can use common sense',
    ])

    assert list(sections_parser.split_by_section(text_fragment, section)) == [
        TextFragment('Text before the list section 💖'),
        section,
        TextFragment('Text after the list section 🛠'),
    ]


def test_split_by_section_no_before_text():
    text_fragment = TextFragment(dedent('''
        Who are you?

        You are a native German speaker
        You love self-management and can use common sense

        Text after the list section 🛠
    '''))
    section = ListSection(heading='Who are you?', contents=[
        'You are a native German speaker',
        'You love self-management and can use common sense',
    ])

    assert list(sections_parser.split_by_section(text_fragment, section)) == [
        section,
        TextFragment('Text after the list section 🛠'),
    ]


def test_split_by_section_no_after_text():
    text_fragment = TextFragment(dedent('''
        Text before the list section 💖

        Who are you?

        You are a native German speaker
        You love self-management and can use common sense
    '''))
    section = ListSection(heading='Who are you?', contents=[
        'You are a native German speaker',
        'You love self-management and can use common sense',
    ])

    assert list(sections_parser.split_by_section(text_fragment, section)) == [
        TextFragment('Text before the list section 💖'),
        section,
    ]


def test_split_by_section_multiple_matches():
    text_fragment = TextFragment(dedent('''
        Text before the list section 💖

        Who are you?

        You are a native German speaker
        You love self-management and can use common sense

        Text between the sections 👀

        Who are you?

        You are a native German speaker
        You love self-management and can use common sense

        Text after the list section 🛠
    '''))
    section = ListSection(heading='Who are you?', contents=[
        'You are a native German speaker',
        'You love self-management and can use common sense',
    ])

    assert list(sections_parser.split_by_section(text_fragment, section)) == [
        TextFragment('Text before the list section 💖'),
        section,
        TextFragment('Text between the sections 👀'),
        section,
        TextFragment('Text after the list section 🛠'),
    ]


def test_split_sentences():
    assert sections_parser.split_sentences(
        'Who we are?\n'
        'What do we do? '
        'Our mission is to create Frankenstein! '
        'Really. '
        'Trust us'
    ) == [
        'Who we are?',
        'What do we do?',
        'Our mission is to create Frankenstein!',
        'Really.',
        'Trust us',
    ]


def test_remove_html_tags():
    el = html.fromstring(dedent('''
        Fronted developer JavaScript, HTML – Praha 3 – HPP/IČO<br>Hledáme
        nového frontend developera.<br><br><strong><u>Co Bys u Nás
        Dělal(a)<br></u></strong>
        <ul>
            <li>Vývoj aplikačního SW.</li>
            <li>Dále se rozvíjet a vzdělávat v rámci pozice.<br></li>
        </ul>
        Požadujeme:Co od tebe očekáváme:<br>
    ''').strip())

    assert sections_parser.remove_html_tags(el) == (
        'Fronted developer JavaScript, HTML – Praha 3 – HPP/IČO\n'
        'Hledáme nového frontend developera.\n'
        'Co Bys u Nás Dělal(a)\n'
        'Vývoj aplikačního SW.\n'
        'Dále se rozvíjet a vzdělávat v rámci pozice.\n'
        'Požadujeme:Co od tebe očekáváme:'
    )