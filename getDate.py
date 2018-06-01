#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import os
import random
import numpy as np
#import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import requests


class HtmlController:
    def __init__(self, _str, _baseURL):
        self.url  = _baseURL
        self.soup = BeautifulSoup(_str, 'html.parser')

    def pareseDate(self):
        text = self.soup.find('span', id='Label_Date').text
        return ''.join(text.split('/'))


class Crawler:
    def __init__(self, _baseURL, _welComeURL):
        self.baseURL    = _baseURL
        self.welcomeURL = _welComeURL
        self.header     = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}
        self.sessObj    = requests.Session()
        self.htmlText   = self.sessObj.get(self.welcomeURL, headers=self.header).text

    def getDate(self):
        cont  = HtmlController(self.htmlText, self.baseURL)
        return cont.pareseDate()



baseURL    = 'http://bsr.twse.com.tw/bshtm/'
welComeURL = 'http://bsr.twse.com.tw/bshtm/bsWelcome.aspx'
cr         = Crawler(baseURL, welComeURL)
print(cr.getDate())
