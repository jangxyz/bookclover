#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib, re, sys
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
    search_pattern = re.compile('''
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

    search_authors_pattern = re.compile('''
            <a[ ].*?class='m'.*?>
                ([^<]*?)               # 작가 이름
            </a>\s*
            ([^<]*)\s*                # 작가 역할
            /?
        ''', re.X)


    @staticmethod
    def search(title=None, isbn=None):
        query = title or str(isbn) or ''
        params = {
            'qdomain': '전체'.decode('utf-8').encode('euc-kr'),
            'query': query.decode('utf-8').encode('euc-kr')
        }
        url = "http://www.yes24.com/searchCenter/searchResult.aspx?" + urllib.urlencode(params)
        #print 'fetching from', url, '...'
        #source = urllib.urlopen(url).read()
        #prefix='<td align="center" valign="top" width="100px">'
        #sources = source.split(prefix)[1:]
        sources = Yes24.fetch(url)

        print 'got', len(sources), 'books (maybe more on next page?)'
        books = map(Yes24.parse_search_result, sources)
        return books

    @staticmethod
    def fetch(url):
        site = urllib.urlopen(url)
        source = site.read()
        #source = source.decode('euc-kr').encode('utf-8')
        #soup = BeautifulSoup(source.decode('euc-kr'))
        prefix='<td align="center" valign="top" width="100px">'

        return source.split(prefix)[1:]


    @staticmethod
    # name, url, series, authors, pulished_at, price, deliverable_at
    def parse_search_result(source):
        match = Yes24.search_pattern.search(source)
        if not match: return 

        result = {}
        for key in ["name", "url", "authors", "price", "deliverable_at", "published_at", "publisher"]:
            if key == "authors": continue 
            result[key] = match.group(key)

        result["authors"] = Yes24.search_authors_pattern.findall(match.group('author_group'))

        return Book(result)

    @staticmethod
    def search_detail(title=None, isbn=None):
        pass


