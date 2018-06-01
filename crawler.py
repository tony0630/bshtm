#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import time
import os
import subprocess
import cv2
import random
import shutil
import numpy as np
#import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import requests

#def showImage(image):
#    plt.imshow(image)
#    plt.show()
def removeNearContour(pos):
    def filterSmall(arr, oriIdx, area):
        mList = list(filter(lambda x: x[1] < 20, arr))
        if mList != []:
            mList += [ (area,0,oriIdx) ]
            remain = max(mList)
            del mList[mList.index(remain)]
            return remain[2], [item[2] for item in mList]
        else:
            return oriIdx, []
    idx = 0
    if len(pos) <= 5:
        return pos
    while idx < 5 and len(pos) > 5:
        x,y,w,h = pos[idx]
        other   = [ (pos[i][2] * pos[i][3],
                     abs(pos[i][0]-x) + abs(pos[i][1]-y),
                     i ) for i in range(idx+1,len(pos)) ]
        rIdx, rmIdx = filterSmall(other, idx, w*h)
        if rmIdx != []:
            pos[idx] = pos[rIdx]
            pos = [data for i,data in enumerate(pos) if i not in rmIdx]
        idx = idx + 1
    return pos


def truncateLength(pos):
    if len(pos) > 5:
        arr = sorted([(w*h,i) for i,(x,y,w,h) in enumerate(pos)], reverse=True)
        return [ pos[i] for i,(x,y,w,h) in enumerate(pos) if (w*h,i) in arr[:5] ]
    else:
        return pos


class HtmlController:
    def __init__(self, _str, _baseURL):
        self.url  = _baseURL
        self.soup = BeautifulSoup(_str, 'html.parser')

    def getCaptchaSrc(self):
        for img in self.soup.find_all('img'):
            src = img.attrs.get(u'src', '')
            if src != '' and 'CaptchaImage.aspx' in src:
                return self.url + src
        print(self.soup.prettify())
        return ''

    def getPostForm(self):
        dic = {}
        obj = self.soup.find('form', id='form1')
        for htmlInput in obj.find_all('input'):
            inType = htmlInput.attrs.get(u'type', None)
            checked = htmlInput.attrs.get(u'checked', None)
            value   = htmlInput.attrs.get(u'value', u'')
            name    = htmlInput.attrs.get(u'name', u'')
            if inType=='radio' and checked == None:
                pass
            elif inType!='submit':
                dic[name] = value
        dic[u'btnOK'] = u'查詢'
        return dic

    def setPostQuery(self, dic, num, code):
        dic['TextBox_Stkno']   = u'' + str(num)
        dic['CaptchaControl1'] = u'' + str(code)
        return dic

    def checkNoData(self):
        return self.soup.find('span', id='Label_ErrorMsg').text == u'查無資料'

    def checkValidSuccess(self):
        return self.soup.find('a', id='HyperLink_DownloadCSV') != None


class Crawler:
    def __init__(self, _baseURL, _menuURL, _contentURL, _savePath=None):
        random.seed()
        self.baseURL    = _baseURL
        self.menuURL    = _menuURL
        self.contentURL = _contentURL
        self.header     = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}
        self.sessObj    = requests.Session()
        self.htmlText   = self.sessObj.get(self.menuURL, headers=self.header).text
        self.savePath   = _savePath

    def refresh(self):
        self.htmlText = self.sessObj.get(self.menuURL, headers=self.header).text

    def getHTML(self):
        return self.htmlText

    def getTargetHTML(self, num, code, outPath):
        cont = HtmlController(self.htmlText, self.baseURL)
        dic  = cont.getPostForm()
        dic  = cont.setPostQuery(dic, num, code)
        res  = self.sessObj.post(menuURL, headers=self.header, data=dic)
        contRes = HtmlController(res.text, self.baseURL)
        self.htmlText = res.text
        if contRes.checkNoData():
            return True
        elif contRes.checkValidSuccess():
            link = self.sessObj.get(self.contentURL, stream=True, headers=self.header)
            with open(outPath, 'wb') as out_file:
                shutil.copyfileobj(link.raw, out_file)
            return True
        else:
            return False

    def getCVimage(self, url):
        dImg  = self.sessObj.get(url, stream=True, headers=self.header)
        rName = str(random.randint(1048576,1073741824)) + '.jpg'
        with open(rName, 'wb') as out_file:
            shutil.copyfileobj(dImg.raw, out_file)
        image = cv2.imread(rName)
        os.remove(rName)
        return image

    def imageToStr(self, fName, path):
        FNULL  = open(os.devnull, 'w')
        params = ' -l eng --psm 10  -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890'
        subprocess.check_output('tesseract ' + path + ' ' +\
                                fName + params , shell=True,\
                                stderr=FNULL)
        if not os.path.isfile(fName+'.txt'):
            return ''
        with open(fName+'.txt','r') as f:
            text = f.read().strip()
        os.remove(fName+'.txt')
        return text

    def splitImage(self, procImg):
        image, contours, hierarchy = cv2.findContours(procImg.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted([(c, cv2.boundingRect(c)[0]) for c in contours], key = lambda x: x[1])
        pos  = []
        for (c,_) in cnts:
            (x,y,w,h) = cv2.boundingRect(c)
            if w > 50 and h > 15:
                pos.append((x,y,w//2,h))
                pos.append((x+w//2,y,w//2,h))
            elif w * h > 280:
                pos.append((x,y,w,h))
        pos = removeNearContour(pos)
        pos = truncateLength(pos)
        text = ''
        for i, (x,y,w,h) in enumerate(pos):
            roi    = procImg[y:y + h, x:x + w]
            thresh = roi.copy()
            thresh = cv2.copyMakeBorder(thresh, top=10, bottom=10,\
                                        left=10, right=10,\
                                        borderType= cv2.BORDER_CONSTANT,\
                                        value=[0,0,0])
            fName = str(i+1)+'.jpg'
            cv2.imwrite(fName, thresh)
            text += self.imageToStr(fName, fName)
        return text

    def crackCode(self):
        def filterThres(img, t1, t2, val):
            for i in range(len(img)):
                for idx, dArr in enumerate(img[i]):
                    img[i][idx] = [ val if t1<=v<=t2 else v for v in dArr  ]
            return img
        cont   = HtmlController(self.htmlText, self.baseURL)
        imgURL = cont.getCaptchaSrc()
        img    = self.getCVimage(imgURL)
        kernel   = np.ones((2,2), np.uint8)
        erosion  = cv2.erode(img, kernel, iterations = 2)
        erosion  = filterThres(erosion, 0, 200, 0)
        blurred  = cv2.GaussianBlur(erosion, (5,5), 3)
        blurred  = filterThres(blurred, 0, 50, 0)
        edged    = cv2.Canny(blurred, 40, 190)
        dilation = cv2.dilate(edged, kernel, iterations = 1)
        return self.splitImage(dilation)

    def getCSV(self, num, trial=10):
        stockId  = str(num)
        count    = 0
        outFname = self.savePath + stockId + '.csv'
        while count < trial:
            code = self.crackCode()
            print(code)
            if len(code) != 5:
                self.refresh()
            elif self.getTargetHTML(stockId, code, outFname):
                break
            count = count + 1


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        sys.exit(0)
    baseURL    = 'http://bsr.twse.com.tw/bshtm/'
    menuURL    = 'http://bsr.twse.com.tw/bshtm/bsMenu.aspx'
    contentURL = 'http://bsr.twse.com.tw/bshtm/bsContent.aspx'
    cr         = Crawler(baseURL, menuURL, contentURL, sys.argv[1])
    with open('./listOfStock.txt', 'r') as fp:
        lines = fp.readlines()
        lines = [ x.strip().split(' ') for x in lines ]
        for x in lines:
            print(x[0] + ', ' + x[1])
            for trial in range(5):
                try:
                    if not os.path.isfile(x[0] + '.csv'):
                        cr.getCSV(x[0])
                        time.sleep(0.5)
                    break
                except Exception as e:
                    print(e)
                    continue

    #print(cr.crackCode())
