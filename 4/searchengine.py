import urllib.request
from bs4 import *
from urllib.parse import urljoin
import sqlite3 as sqlite
import re


ignorewords = set(['the', 'of', 'to', 'and', 'a', 'in', 'is', 'it'])

class crawler(object):
    """docstring for crawler."""
    def __init__(self, dbname):
        self.con = sqlite.connect(dbname)

    def __del__(self):
        self.con.close()
    def dbcommit(self):
        self.con.commit()

    def getentryid(self, table, field, value, createnew=True):
        cur = self.con.execute("select rowid from %s where %s=?" % (table,field), (value,))
        res = cur.fetchone()
        if res == None:
            cur = self.con.execute("insert into %s(%s) values (?)" %(table,field), (value,))
            return cur.lastrowid
        else:
            return res[0]

    def addtoindex(self, url, soup):
        if self.isindexed(url): return
        print('Indexing ' + url)

        text = self.gettextonly(soup)
        words = self.separatewords(text)

        urlid = self.getentryid("urllist", "url", url)

        for i in range(len(words)):
            word = words[i]
            if word in ignorewords: continue
            wordid = self.getentryid('wordlist', 'word', word)
            self.con.execute('insert into wordlocation(urlid, wordid, location) \
                                values(?, ?, ?)', (urlid, wordid, i))

    def gettextonly(self, soup):
        v = soup.string
        if v == None:
            c = soup.contents
            resulttext = ''
            for t in c:
                subtext = self.gettextonly(t)
                resulttext += subtext +'\n'
            return resulttext
        else:
            return v.strip()

    def separatewords(self, text):
        splitter = re.compile('\\W*')
        return [s.lower() for s in splitter.split(text) if s!='']

    def isindexed(self, url):
        u = self.con.execute("select rowid from urllist where url=?",(url,)).fetchone()
        if u!= None:
            v = self.con.execute('select * from wordlocation where urlid = ?', (u[0],)).fetchone()
            if v!=None: return True
        return False

    def addlinkref(self, urlFrom, urlTo, linkText):
        words=self.separatewords(linkText)
        fromid=self.getentryid('urllist','url',urlFrom)
        toid=self.getentryid('urllist','url',urlTo)
        if fromid==toid: return
        cur=self.con.execute("insert into link(fromid,toid) values (?,?)", (fromid,toid))
        linkid=cur.lastrowid
        for word in words:
          if word in ignorewords: continue
          wordid=self.getentryid('wordlist','word',word)
          self.con.execute("insert into linkwords(linkid,wordid) values (?,?)", (linkid,wordid))


    def crawl(self, pages, depth=2):
        for i in range(depth):
            newpages = set()
            for page in pages:
                try:
                    c = urllib.request.urlopen(page)
                except:
                    print("Could not open %s" % page)
                    continue
                soup = BeautifulSoup(c.read(), 'html5lib')
                self.addtoindex(page, soup)

                links = soup('a')
                for link in links:
                    print(link)
                    if ('href' in dict(link.attrs)):
                        print(123)
                        url = urljoin(page, link['href'])
                        print(url)
                        if url.find("'") != -1: continue

                        url = url.split('#')[0]
                        if url[0:4] == 'http' and not self.isindexed(url):
                            newpages.add(url)
                        linkText = self.gettextonly(link)
                        self.addlinkref(page, url, linkText)

                self.dbcommit()
            pages = newpages
            print(pages)

    def createindextables(self):
        self.con.execute('create table urllist(url)')
        self.con.execute('create table wordlist(word)')
        self.con.execute('create table wordlocation(urlid, wordid, location)')
        self.con.execute('create table link(fromid integer, toid integer)')
        self.con.execute('create table linkwords(wordid, linkid)')
        self.con.execute('create index wordidx on wordlist(word)')
        self.con.execute('create index urlidx on urllist(url)')
        self.con.execute('create index wordurlidx on wordlocation(wordid)')
        self.con.execute('create index urltoidx on link(toid)')
        self.con.execute('create index urlfromidx on link(fromid)')
        self.dbcommit()


class searcher:
    def __init__(self, dbname):
        self.con = sqlite.connect(dbname)

    def __del__(self):
        self.con.close()

    def getmatchrows(self, q):
        '''接受一个待搜索字符串q作为参数，并将其拆分为多个单词，然后构造一个SQL查询，只查找那些包含所有不同单词的URL
            返回 rows = [(w0.urlid, w0.location, w1.location),]  wordid = [wo.id, w1,id]
        example:
          select w0.urlid, w0.location, w1.location
          from wordlocation w0, wordlocation w1
          where w0.urlid=w1.urlid
          and w0.wordid=10
          and w1.wordid=17
        '''
        fieldlist = 'w0.urlid'
        tablelist = ''
        clauselist = ''
        wordids = []

        #根据空格拆分单词
        words = q.split(' ')
        tablenumber = 0

        for word in words:
            #获取单词的ID
            wordrow = self.con.execute("select rowid from wordlist where word = ?", (word,)).fetchone()
            if wordrow != None:
                wordid = wordrow[0]
                wordids.append(wordid)
                if tablenumber > 0:
                    tablelist += ','
                    clauselist += ' and '
                    clauselist += 'w%d.urlid = w%d.urlid and ' % (tablenumber-1, tablenumber)
                fieldlist += ', w%d.location' % tablenumber
                tablelist +=  'wordlocation w%d' % tablenumber
                clauselist += 'w%d.wordid = %d' % (tablenumber, wordid)
                tablenumber += 1

        fullquery = 'select %s from %s where %s' % (fieldlist, tablelist, clauselist)
        cur = self.con.execute(fullquery)
        rows = [row for row in cur]

        return rows, wordids


    def getscoredlist(self, rows, wordids):
        totalscores = dict([(row[0], 0) for row in rows])

        weights = []

        for (weight, scores) in weights:
            for url in totalscores:
                totalscores[url] += weight * scores[url]

        return totalscores

    def geturlname(self, id):
        return self.con.execute("select url from urllist where rowid = %d" % id).fetchone()[0]

    def query(self, q):
        rows, wordids = self.getmatchrows(q)
        scores = self.getscoredlist(rows, wordids)
        rankedscores = sorted([(score, url) for (url, score) in scores.items()], reverse = 1)
        for (score, urlid) in rankedscores[0:10]:
            print("%f\t%s" %(score, self.geturlname(urlid)))

if __name__ == '__main__':
    #crawler = crawler('searchindex.db')
    #crawler.createindextables()
    #page=["http://linzb.xyz/"]
    #crawler.crawl(page)

    e = searcher('searchindex.db')
    #print(e.getmatchrows('linzb python'))
    e.query('linzb learning')
