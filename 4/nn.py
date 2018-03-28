from math import tanh
import sqlite3 as sqlite

def dtanh( y):
    #tanh(x)的倒数
    return 1 - y*y

class searchnet:
    def __init__(self, dbname):
        self.con = sqlite.connect(dbname)

    def __del__(self):
        self.con.close()

    def maketable(self):
        self.con.execute('create table hiddennodes(create_key)')
        self.con.execute('create table wordhidden(fromid, toid, strength)')
        self.con.execute('create table hiddenurl(fromid, toid, strength)')
        self.con.commit()

    def getstrength(self, fromid, toid, layer):
        #从数据库查询连接强度 默认值分别为：-0.2 0
        if layer == 0:
            table = 'wordhidden'
        else:
            table = 'hiddenurl'

        res = self.con.execute('select strength from %s where fromid = %d and toid = %d'
                                        % (table, fromid, toid)).fetchone()
        if res == None:
            if layer == 0:
                return -0.2
            if layer == 1:
                return 0
        else:
            return res[0]

    def setstrength(self, fromid, toid, layer, strength):
        #设置（更新）连接强度
        if layer == 0:
            table = 'wordhidden'
        else:
            table = 'hiddenurl'
        res = self.con.execute('select rowid from %s where fromid = %d and toid = %d'
                                        %(table, fromid, toid)).fetchone()
        if res == None:
            self.con.execute('insert into %s (fromid, toid, strength) values(%d, %d, %f)'
                                        %(table, fromid, toid, strength))
        else:
            rowid = res[0]
            self.con.execute('update %s set strength = %f where rowid = %d' %(table, strength, rowid))

    def generatehiddennode(self, wordids, urls):
        #输入wordid的list 和对应的url的list 生成隐藏层节点
        if len(wordids) > 3: return None

        #检查我们是否已经为这组单词建立好了一个结点
        createkey = '_'.join(sorted([str(wi) for wi in wordids])) #产生:w1_w2_w3
        res = self.con.execute("select rowid from hiddennodes where create_key ='%s'" %(createkey)).fetchone()

        #如果没有，则建立
        if res == None:
            cur = self.con.execute("insert into hiddennodes(create_key) values('%s')" %(createkey))
            hiddenid = cur.lastrowid
            #设置默认权重
            for wordid in wordids:
                self.setstrength(wordid, hiddenid, 0, 1.0/len(wordids)) #默认权重为1/len(wordids)
            for url in urls:
                self.setstrength(hiddenid, url, 1, 0.1)     #默认权重值为0.1
            self.con.commit()


    def getallhiddenids(self, wordids, urlids):
        #从数据库中取出与当前要查询的wordids、urlids相关联的隐藏层节点
        l1 = {}
        for wordid in wordids:
            cur = self.con.execute('select toid from wordhidden where fromid = %d' % wordid)
            for row in cur: l1[row[0]] = 1
        for urlid in urlids:
            cur = self.con.execute('select fromid from hiddenurl where toid = %d' % urlid)
            for row in cur: l1[row[0]] = 1
        return list(l1.keys())      #在python3中使用dict.keys()返回的不在是list类型了，也不支持索引

    def setupnetwork(self, wordids, urlids):
        #建立起与当前要查询的wordids、urlids相关的神经网络
        self.wordids = wordids
        self.hiddenids = self.getallhiddenids(wordids, urlids)
        self.urlids = urlids

        #初始化 节点上的值
        self.ai = [1.0] * len(self.wordids)
        self.ah = [1.0] * len(self.hiddenids)
        self.ao = [1.0] * len(self.urlids)

        #输入层到隐藏层权重
        self.wi = [[self.getstrength(wordid, hiddenid, 0)
                        for hiddenid in self.hiddenids]
                        for wordid in self.wordids]
        #隐藏层到输出层权重
        self.wo = [[self.getstrength(hiddenid, urlid, 1)
                        for urlid in self.urlids]
                        for hiddenid in self.hiddenids]

    def feedforward(self):
        #初始化神经网络的输入
        for i in range(len(self.wordids)):
            self.ai[i] = 1.0

        #计算隐藏层节点的活跃程度
        for j in range(len(self.hiddenids)):
            sum = 0.0
            for i in range(len(self.wordids)):
                sum = sum + self.ai[i] * self.wi[i][j]
            self.ah[j] = tanh(sum)

        #计算输出层节点的活跃程度
        for k in range(len(self.urlids)):
            sum = 0.0
            for j in range(len(self.hiddenids)):
                sum = sum + self.ah[j] * self.wo[j][k]
            self.ao[k] = tanh(sum)
        #返回输出层节点的活跃程度
        return self.ao[:]

    def getresult(self, wordids, urlids):
        self.setupnetwork(wordids, urlids)
        return self.feedforward()

    def backPropagate(self, targets, N = 0.5):
        #计算输出层的误差
        output_deltas = [0.0] * len(self.urlids)
        for k in range(len(self.urlids)):
            error = targets[k] - self.ao[k]
            output_deltas[k] = dtanh(self.ao[k]) * error

        #计算隐藏层误差
        hidden_deltas = [0.0] * len(self.hiddenids)
        for j in range(len(self.hiddenids)):
            error = 0.0
            for k in range(len(self.urlids)):
                error = error + output_deltas[k] * self.wo[j][k]
            hidden_deltas [j] = dtanh(self.ah[j]) * error

        #更新隐藏层-输出层权重
        for j in range(len(self.hiddenids)):
            for k in range(len(self.urlids)):
                change = output_deltas[k] * self.ah[j]
                self.wo[j][k] = self.wo[j][k] + N * change

        #更新输入层-隐藏层权重
        for i in range(len(self.wordids)):
            for j in range(len(self.hiddenids)):
                change = hidden_deltas[j] * self.ai[i]
                self.wi[i][j] = self.wi[i][j] + N * change

    def trainquery(self, wordids, urlids, selectedurl):
        #建立神经网络，运行前向传播、反向传播算法 存入数据库中
        self.generatehiddennode(wordids, urlids)

        self.setupnetwork(wordids, urlids)
        self.feedforward()
        targets = [0.0] * len(urlids)
        targets[urlids.index(selectedurl)] = 1.0
        self.backPropagate(targets)
        self.updatedatabase()


    def updatedatabase(self):
        for i in range(len(self.wordids)):
            for j in range(len(self.hiddenids)):
                self.setstrength(self.wordids[i], self.hiddenids[j], 0, self.wi[i][j])
        for j in range(len(self.hiddenids)):
            for k in range(len(self.urlids)):
                self.setstrength(self.hiddenids[j], self.urlids[k], 1, self.wo[j][k])
        self.con.commit()


if __name__ == '__main__':
    '''mynet = searchnet('nn.db')
    #mynet.maketable()
    wWorld, wRiver, wBank = 101, 102, 103
    uWorldBank, uRiver, uEarth = 201,202,203
    mynet.generatehiddennode([wWorld, wBank], [uWorldBank, uRiver, uEarth])
    for c in mynet.con.execute('select * from wordhidden'):
        print(c)
    for c in mynet.con.execute('select * from hiddenurl'):
        print(c)


    wWorld, wRiver, wBank = 101, 102, 103
    uWorldBank, uRiver, uEarth = 201,202,203
    mynet = searchnet('nn.db')
    print(mynet.getresult([wWorld, wBank], [uWorldBank, uRiver, uEarth]))
    '''

    wWorld, wRiver, wBank = 101, 102, 103
    uWorldBank, uRiver, uEarth = 201,202,203
    mynet = searchnet('nn.db')

    mynet.trainquery([wWorld, wBank], [uWorldBank, uRiver, uEarth], uWorldBank)
    print(mynet.getresult([wWorld, wBank], [uWorldBank, uRiver, uEarth]))

    res = mynet.con.execute('select * from hiddenurl where fromid = 0 and toid = 0').fetchone()
    print(res)
