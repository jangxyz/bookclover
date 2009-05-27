#!/usr/bin/python
# -*- encoding: utf-8 -*-

from bookclub import *

#
def is_search_result(result):
    type(search_result) is list

def test_search():
    search_result = Yes24.search(title='북클럽')
    search_result = Yes24.search(isbn=8988674472)
    search_result = Yes24.search(isbn='899087212X')


#
def test_search_detail():
    detail_result = Yes24.search_detail(title='북클럽')
    detail_result = Yes24.search(isbn=8988674472)
    detail_result = Yes24.search(isbn='899087212X')


