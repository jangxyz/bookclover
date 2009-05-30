#!/usr/bin/python
# -*- encoding: utf-8 -*-

import unittest
from bookclub import *


source = open("yes24.html").read()

def result_check_tuple(result):
    return [
        (type(result) == list, "result should be a list"),
        (len(result) == 20,    "result should have 20 items"),
        (type(result[0]) == Book, "item of result should be an instance of Book"),
        (result[0].name == "여우의 전화 박스", "expected '여우의 전화 박스', but got '%s'" % (result[0].name)),
    ]

def is_correct_result(result):
    for check, errmsg in result_check_tuple(result):
        assert check, errrmsg
    #assert type(result) == list, "result should be a list"
    #assert len(result) == 20, "result should have 20 items"
    #assert type(result[0]) == Book, "item of result should be an instance of Book"
    #assert result[0].name == "여우의 전화 박스", "expected '여우의 전화 박스', but got '%s'" % (result[0].name)


def test_without_mock():
    pass

def execute_code_and_assert():
    search_result = Yes24.search(title='북클럽')
    is_correct_result(search_result)



def test_PythonMock():
    from mocks import python_mock as mock
    original_urlopen = urllib.urlopen
    # mock
    #mocked_urlopen = mock.Mock( {"read": source} )
    #mocked_urllib  = mock.Mock( {"urlopen": mocked_urlopen} )
    #urllib.urlopen = mocked_urllib.urlopen
    urllib.urlopen = mock.Mock( {"read": source} )

    execute_code_and_assert

    urllib.urlopen = original_urlopen


def test_PyMock():
    from mocks import pymock
    c = pymock.Controller()
    # record: when I do this,
    mocked_urlopen = c.mock()
    c.expectAndReturn(mocked_urlopen.read(), source)
    c.override(urllib, 'urlopen')
    c.expectAndReturn(urllib.urlopen('http://www.yes24.com/searchCenter/searchResult.aspx?query=%BA%CF%C5%AC%B7%B4&qdomain=%C0%FC%C3%BC'), mocked_urlopen)

    # replay: remember to do this
    c.replay()
    execute_code_and_assert()
    
    # verify: now go!
    c.verify()


from mocks import voidspace_mock as mock
@mock.patch('urllib.urlopen')
def test_VoidspaceMock(mocked_urlopen):
    mocked_urlopen.return_value.read.return_value = source

    execute_code_and_assert()
    

def test_pMock():
    from mocks import pmock
    original_urlopen = urllib.urlopen

    # mock
    mocked_urlopen = pmock.Mock()
    mocked_urlopen.expects(pmock.once()).read().will(pmock.return_value(source))
    urllib.urlopen = lambda x: mocked_urlopen

    execute_code_and_assert()

    urllib.urlopen = original_urlopen

    #mocked_urllib.verify()

