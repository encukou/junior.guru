from collections import namedtuple
from datetime import datetime, date

import pytest

from juniorguru.web import template_filters


def test_email_link():
    markup = str(template_filters.email_link('xyz@example.com'))
    assert markup == '<a href="mailto:xyz&#64;example.com">xyz&#64;<!---->example.com</a>'


def test_remove_p():
    markup = str(template_filters.remove_p('<p>call me <b>maybe</b></p>  \n<p class="hello">call me Honza</p>'))
    assert markup == 'call me <b>maybe</b>  \ncall me Honza'


@pytest.mark.parametrize('dt_str,expected', [
    ('2020-04-21 12:01:48', datetime(2020, 4, 21, 12, 1, 48)),
    ('2020-04-21T12:01:48', datetime(2020, 4, 21, 12, 1, 48)),
])
def test_to_datetime(dt_str, expected):
    assert template_filters.to_datetime(dt_str) == expected


@pytest.mark.parametrize('dt,expected', [
    (date(2019, 12, 10), 'dnes'),
    (datetime(2019, 12, 10, 16, 20, 42), 'dnes'),
    (datetime(2019, 12, 9, 16, 20, 42), 'včera'),
    (datetime(2019, 12, 8, 16, 20, 42), 'předevčírem'),
    (datetime(2019, 12, 7, 16, 20, 42), 'před 3 dny'),
    (datetime(2019, 11, 30, 16, 20, 42), 'před 10 dny'),
    (datetime(2019, 10, 31, 16, 20, 42), 'před 40 dny'),
])
def test_ago(dt, expected):
    now = datetime(2019, 12, 10, 16, 20, 42)
    assert template_filters.ago(dt, now=now) == expected


@pytest.mark.parametrize('section,expected', [
    pytest.param(
        dict(heading='Offer', type='list', contents=['work', 'money']),
        '\n'.join([
            '- heading: Offer',
            '  type: list',
            '  contents:',
            '    - work',
            '    - money',
        ]),
        id='list',
    ),
    pytest.param(
        dict(type='list', contents=['work', 'money']),
        '\n'.join([
            '- type: list',
            '  contents:',
            '    - work',
            '    - money',
        ]),
        id='list_no_heading',
    ),
    pytest.param(
        dict(type='paragraph', contents=['work', 'money']),
        '\n'.join([
            '- type: paragraph',
            '  contents:',
            '    - work',
            '    - money',
        ]),
        id='paragraph',
    ),
    pytest.param(
        dict(heading='We offer:', type='list', contents=['work', 'money']),
        '\n'.join([
            '- heading: "We offer:"',
            '  type: list',
            '  contents:',
            '    - work',
            '    - money',
        ]),
        id='colon_heading',
    ),
    pytest.param(
        dict(type='list', contents=['work', 'must have: hands', 'money']),
        '\n'.join([
            '- type: list',
            '  contents:',
            '    - work',
            '    - "must have: hands"',
            '    - money',
        ]),
        id='colon_contents',
    ),
])
def test_sections_paragraph(section, expected):
    assert template_filters.sections([section]) == expected


def test_sections_multiple():
    sections = [
        dict(heading='Offer', type='list', contents=['work', 'money']),
        dict(heading='Must have', type='list', contents=['PHP', 'C#']),
    ]

    assert template_filters.sections(sections) == '\n'.join([
        '- heading: Offer',
        '  type: list',
        '  contents:',
        '    - work',
        '    - money',
        '',
        '- heading: Must have',
        '  type: list',
        '  contents:',
        '    - PHP',
        '    - C#',
    ])


@pytest.mark.parametrize('value,expected', [
    pytest.param(134, '130', id='hundreds'),
    pytest.param(2179, '2200', id='thousands'),
    pytest.param(21790, '22tis', id='tens thousands'),
    pytest.param(4270, '4300', id='round up'),
    pytest.param(4250, '4300', id='round half up'),
    pytest.param(4240, '4200', id='round down'),
    pytest.param(4240.542, '4200', id='float'),
])
def test_metric(value, expected):
    assert template_filters.metric(value) == expected


@pytest.mark.parametrize('items,n,expected', [
    pytest.param(
        ['x'],
        4,
        {'x'},
        id='len(items) < n',
    ),
    pytest.param(
        ['x', 'y'],
        2,
        {'x', 'y'},
        id='len(items) == n',
    ),
])
def test_sample(items, n, expected):
    assert set(template_filters.sample(items, n)) == expected


def test_sample_random():
    random_called = False

    def random_sample(items, n):
        nonlocal random_called
        random_called = True
        return items[:n]

    assert set(template_filters.sample(['x', 'y', 'z'], 2, sample_fn=random_sample)) == {'x', 'y'}
    assert random_called is True



DummyJob = namedtuple('Job', ['id', 'source'])


@pytest.mark.parametrize('jobs,n,expected', [
    pytest.param(
        [DummyJob(id=1, source='xyz'), DummyJob(id=2, source='xyz')],
        4,
        {DummyJob(id=1, source='xyz'), DummyJob(id=2, source='xyz')},
        id='len(jobs) < n',
    ),
    pytest.param(
        [DummyJob(id=1, source='xyz'), DummyJob(id=2, source='xyz')],
        2,
        {DummyJob(id=1, source='xyz'), DummyJob(id=2, source='xyz')},
        id='len(jobs) == n',
    ),
    pytest.param(
        [DummyJob(id=1, source='xyz'), DummyJob(id=2, source='juniorguru'), DummyJob(id=3, source='juniorguru')],
        2,
        {DummyJob(id=2, source='juniorguru'), DummyJob(id=3, source='juniorguru')},
        id='preferred jobs have priority',
    ),
])
def test_sample_jobs(jobs, n, expected):
    assert set(template_filters.sample_jobs(jobs, n)) == expected


def test_sample_jobs_not_enough_preferred_jobs():
    random_called = False

    def random_sample(jobs, n):
        nonlocal random_called
        random_called = True
        return jobs[:n]

    assert set(template_filters.sample_jobs([
        DummyJob(id=1, source='xyz'),
        DummyJob(id=2, source='juniorguru'),
        DummyJob(id=3, source='xyz')
    ], 2, sample_fn=random_sample)) == {
        DummyJob(id=1, source='xyz'),
        DummyJob(id=2, source='juniorguru'),
    }
    assert random_called is True
