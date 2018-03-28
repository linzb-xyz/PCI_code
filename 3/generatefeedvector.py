import feedparser
import re

def getwordcount(url):
    d = feedparser.parse(url)
    wc = {}

    for e in d.entries: #每个entries是一篇文章（html格式）
        if 'summary' in e:  summary = e.summary
        else:   summary = e.description

        words = getwords(e.title + ' ' + summary)
        for word in words:
            wc.setdefault(word, 0)
            wc[word] += 1
    return d.feed.title, wc     #feed.title是博客的名称， wc是{单词：单词数}

def getwords(html):
    txt = re.compile(r'<[^>]+>').sub(' ', html)

    words = re.compile(r'[^A-Z^a-z]+').split(txt)

    return [word.lower() for word in words if word != ' ' ]

if __name__ == '__main__':

    apcount ={} #记录出现某一单词的博客数
    wordcounts = {}
    feedlist = [line for line in open('F:\\CI\\3\\feedlist.txt')]
    for feedurl in feedlist:
        try:
            title, wc = getwordcount(feedurl)
            wordcounts[title] = wc
            for word, count in wc.items():
                apcount.setdefault(word, 0)
                if count > 1:
                    apcount[word] += 1
        except:
            print('Failed to parse feed %s' %feedurl)
    wordlist = []
    for w, bc in apcount.items():
        frac = float(bc) / len(feedlist)
        if frac > 0.1 and frac < 0.5: wordlist.append(w)

    out = open('blogdata.data','w')
    out.write('Blog')
    for word in wordlist:
            out.write('\t%s' %word)
    out.write('\n')

    for blog, wc in wordcounts.items():
        out.write(blog)
        for word in wordlist:
            if word in wc:
                out.write('\t%d' % wc[word])
            else:
                out.write('\t0')
        out.write('\n')
