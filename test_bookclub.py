#!/usr/bin/python
# -*- encoding: utf-8 -*-

import unittest
from bookclub import *

#

def is_search_result(self, result):
    assert type(search_result) is list

def mock_search():
    

@with_setup(mock_search, None)
def test_search():
    search_result = Yes24.search(title='북클럽')
    search_result = Yes24.search(isbn=8988674472)
    search_result = Yes24.search(isbn='899087212X')


class Yes24SearchDetailTest:
    def test_search_detail():
        detail_result = Yes24.search_detail(title='북클럽')
        detail_result = Yes24.search(isbn=8988674472)
        detail_result = Yes24.search(isbn='899087212X')


