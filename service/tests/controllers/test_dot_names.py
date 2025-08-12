from service.helpers.dot_name import DotName
from unittest.mock import patch
from tests.conftest import client


# Reversible dot name pairs for testing the two ancestor/descendant methods
ANCESTOR_TRUE = 1
DESCENDANT_TRUE = -1
NONE_TRUE = None
ancestor_descendant_pairs = {
    ('Africa', 'Africa'): {'relationship': NONE_TRUE, 'distance': 0},
    ('Africa', 'Africa:Mali'): {'relationship': ANCESTOR_TRUE, 'distance': -1},
    ('Africa', 'Africa:Mali:Gao'): {'relationship': ANCESTOR_TRUE, 'distance': -2},
    ('Africa:Mali:Gao', 'Africa'): {'relationship': DESCENDANT_TRUE, 'distance': 2},
    ('Africa:Mali', 'Africa:Mali:Gao:A:B:C:D'): {'relationship': ANCESTOR_TRUE, 'distance': -5},
    ('Africa:Mali', 'Africa:Senegal'): {'relationship': NONE_TRUE, 'distance': None},
    ('Africa:Mali:Gao', 'Africa:Senegal:Gao'): {'relationship': NONE_TRUE, 'distance': None},
    ('Africa:Mali', 'Africa:Senegal:Dakar'): {'relationship': NONE_TRUE, 'distance': None},
    ('Africa:Mali', 'Europe:Italy'): {'relationship': NONE_TRUE, 'distance': None}
}


# DotName unit tests
def test_valid_dot_name_strings():
    '''
    Test validity of various dotnames
    '''
    DotName(dot_name_str='Africa')
    DotName(dot_name_str='Africa:Kenya')
    DotName(dot_name_str='Africa:Kenya:some_province')
    DotName(dot_name_str='Africa:Kenya:some__other--province')
    DotName(dot_name_str='A:F:R:I:C:A:K:E:N:Y:A')
    DotName(dot_name_str='Earth:Mars:Belt')


def test_country_property():
    '''
    Test recognition of country property in dotname structure
    '''
    assert DotName(dot_name_str='Africa').country is None
    assert DotName(dot_name_str='Africa:Kenya').country == 'Kenya'
    assert DotName(dot_name_str='Africa:Kenya:SomePlace').country == 'Kenya'


def test_continent_property():
    '''
    Test recognition of continent property in dotname structure
    '''
    assert DotName(dot_name_str='Africa').continent == 'Africa'
    assert DotName(dot_name_str='Africa:Kenya').continent == 'Africa'


def test_admin_level_property():
    '''
    Test recognition of admin level in dotname structure
    '''
    assert DotName(dot_name_str='Africa').admin_level == 0
    assert DotName(dot_name_str='Africa:Kenya:SomePlace').admin_level == 2


def test_equality():
    '''
    Test recognition of equivalence of dotnames with varying country and admin levels
    '''
    assert DotName(dot_name_str='Africa') == DotName(dot_name_str='Africa')
    assert DotName(dot_name_str='Africa:Kenya') == DotName(dot_name_str='Africa:Kenya')
    assert DotName(dot_name_str='Africa:Kenya') != DotName(dot_name_str='Africa:Nigeria')
    assert DotName(dot_name_str='Africa:Kenya') != DotName(dot_name_str='Africa:Kenya:SomePlace')


def test_is_ancestor_and_is_descendant():
    '''
    Test integrity of ancestor/descendant relationships among hierarchy in dotnames
    '''
    for dn_str_pair, expected in ancestor_descendant_pairs.items():
        expected = expected['relationship']
        dn1 = DotName(dot_name_str=dn_str_pair[0])
        dn2 = DotName(dot_name_str=dn_str_pair[1])
        if expected is ANCESTOR_TRUE:
            assert dn1.is_ancestor(dn=dn2)
            assert not dn1.is_descendant(dn=dn2)
        elif expected is DESCENDANT_TRUE:
            assert not dn1.is_ancestor(dn=dn2)
            assert dn1.is_descendant(dn=dn2)
        elif expected is NONE_TRUE:
            assert not dn1.is_ancestor(dn=dn2)
            assert not dn1.is_descendant(dn=dn2)
        else:
            raise Exception(f'Unknown expected result case: {expected}')


def test_generational_distance():
    '''
    Test that generational distance between dotnames is calculated correctly
    '''
    for dn_str_pair, expected in ancestor_descendant_pairs.items():
        expected = expected['distance']
        dn1 = DotName(dot_name_str=dn_str_pair[0])
        dn2 = DotName(dot_name_str=dn_str_pair[1])
        assert expected == dn1.generational_distance(dn=dn2)


def test_from_parts():
    '''
    Test that from_parts can correctly parse dotname attributes
    '''
    dn = DotName.from_parts(parts=['Africa'])
    assert dn.admin_level == 0
    assert dn.continent == 'Africa'
    assert dn.country is None

    dn = DotName.from_parts(parts=['Africa', 'Senegal', 'Dakar'])
    assert dn.admin_level == 2
    assert dn.continent == 'Africa'
    assert dn.country == 'Senegal'


# Endpoint tests

@patch("service.controllers.dot_names.read_dot_names", return_value=["Africa"])
@patch("service.controllers.dot_names.get_child_dot_names", return_value=["Africa:Senegal"])
def test_get_dot_names_success(mock_get_child_dot_names, mock_read_dot_names, client):
    '''
    Test successful endpoint
    '''
    response = client.get("/dot_names?dot_name=Africa")
    assert response.status_code == 200
    assert response.json() == {
        "dot_names": [{'id': 'Africa:Senegal', 'text': 'Senegal'}]
    }


@patch("service.controllers.dot_names.read_dot_names", return_value=["Africa", "Asia"])
def test_get_dot_names_multiple_parents_error(mock_read_dot_names, client):
    '''
    Test that only one dotname can be requested
    '''
    response = client.get("/dot_names?dot_name=Africa,Asia")
    assert response.status_code == 400
    assert "child dot_names can only be requested" in response.text


@patch("service.controllers.dot_names.read_dot_names", return_value=["Africa:Benin:Borgou"])
@patch("service.controllers.dot_names.get_child_dot_names", return_value=[])
def test_get_dot_names_empty(mock_get_child_dot_names, mock_read_dot_names, client):
    '''
    Test that empty dotname cannot be provided
    '''
    response = client.get("/dot_names?dot_name=Africa:Benin:Borgou")
    assert response.status_code == 200
    assert response.json() == {"dot_names": []}


def test_get_dot_names_invalid_format(client):
    '''
    Test correct format of dotname query param
    '''
    response = client.get("/dot_names?dot_name=Invalid::::Name")
    assert response.status_code == 400


def test_get_dot_names_missing_query_param(client):
    '''
    Test that dotname must be provided
    '''
    response = client.get("/dot_names")
    assert response.status_code == 400
