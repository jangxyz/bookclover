#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib
#from BeautifulSoup import BeautifulSoup
#from BaseHTMLProcessor import BaseHTMLProcessor

class Book(dict):
    def __init__(self, _dict):
        for key, value in _dict.iteritems():
            setattr(self, key, value)
            self[key] = value

class Bookclub:
    def asdf():
        pass


class Yes24:

    @staticmethod
    def search(title=None, isbn=None):
        params = {
            'qdomain': '전체'.decode('utf-8').encode('euc-kr'),
            'query': title.decode('utf-8').encode('euc-kr')
        }
        url = "http://www.yes24.com/searchCenter/searchResult.aspx?" + urllib.urlencode(params)
        print 'fetching from', url, '...'
        source = urllib.urlopen(url).read()
        print 'OK'
        '''
			<table id="tblProductList" width="100%" cellspacing="0" cellpadding="0" border="0" style="padding : 20 0 20 0">
        '''
        #soup = BeautifulSoup(source.decode('euc-kr'))
        prefix='<td align="center" valign="top" width="100px">'

        sources = source.split(prefix)[1:]
        print 'got', len(sources), 'books (maybe more on next page?)'
        books = map(self.parse_search_result, sources)
        return books

    @staticmethod
    # name, url, series, authors, pulished_at, price, deliverable_at
    def parse_search_result(source):
        pattern = re.compile('''
            <a[ ]href=['"](?P<url>.*?)['"]>             # 페이지 url
              <b>(?P<name>.*?)</b>                      # 책 제목
            </a>\s*
            (
                <span[ ]class=['"]info['"]>
                    (?P<series>.*?)                     # 책 시리즈
                </span>
            )?
            .*
            <span[ ]class="txtAp">
              (?P<author_group>.*?)\s*[|]\s*            # 작가 그룹
              <a[ ].*?>(?P<publisher>.*?)</a>           # 출판사
              \s*[|]\s*
              (?P<published_at>.*?)                     # 출판일자
            </span>\s*
            <div[ ]style="margin-top:5">.*
              <span[ ]class='priceB'>
                (?P<price>.*?)                          # 공급가격
              </span>
              .*?
              <div[ ]style="margin-top:5">
                도착[ ]예상일[ ]:[ ]지금[ ]주문하면[ ]
                <b>(?P<deliverable_at>.*?)</b>          # 예상 수령일
                [ ]받을[ ]수[ ]있습니다.
        ''', re.S | re.X)
        match = pattern.search(source)

        result = {}
        for key in ["name", "url", "authors", "price", "deliverable_at", "published_at", "publisher"]:
            if key == "authors":
                continue 
            result[key] = match.group(key)

        pattern_authors = re.compile('''
            <a[ ].*?class='m'.*?>
                (.*?)               # 작가 이름
            </a>\s*
            (.*?)                   # 작가 역할
            \s*[/]?
        ''', re.X)
        result["authors"] = pattern_authors.findall(match.group('author_group'))

        return Book(result)

    @staticmethod
    def search_detail(title=None, isbn=None):
        pass


