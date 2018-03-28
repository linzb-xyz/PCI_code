from math import sqrt

critics={
'Lisa Rose': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5,
'The Night Listener': 3.0},

'Gene Seymour': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5,
'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0,
'You, Me and Dupree': 3.5},

'Michael Phillips': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
'Superman Returns': 3.5, 'The Night Listener': 4.0},

'Claudia Puig': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
'The Night Listener': 4.5, 'Superman Returns': 4.0,
'You, Me and Dupree': 2.5},

'Mick LaSalle': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
'You, Me and Dupree': 2.0},

'Jack Matthews': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},

'Toby': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0}
}


def sim_distance(prefs,person1,person2):
    '''相似性度量方法：欧几里德距离'''
    si={}
    for item in prefs[person1]:
        if item in prefs[person2]: si[item]=1

    if len(si) == 0: return 0

    sum_of_squares = sum([pow(prefs[person1][item]-prefs[person2][item],2)
                        for item in prefs[person1] if item in prefs[person2]])

    return 1/(1+sqrt(sum_of_squares))

def sim_pearson(prefs,p1,p2):
    '''相似性度量方法：皮尔逊相关系数'''
    si={}
    for item in prefs[p1]:
        if item in prefs[p2]: si[item] = 1
    n=len(si)

    if n==0:
        return 0

    sum1 = sum([prefs[p1][it] for it in si])
    sum2 = sum([prefs[p2][it] for it in si])

    sum1Sq = sum([pow(prefs[p1][it],2) for it in si])
    sum2Sq = sum([pow(prefs[p2][it],2) for it in si])

    pSum = sum([prefs[p1][it]*prefs[p2][it] for it in si])

    num = pSum-(sum1*sum2/n)
    den = sqrt((sum1Sq-pow(sum1,2)/n)*(sum2Sq-pow(sum2,2)/n))
    if den==0: return 0
    r = num/den
    return r

def topMatches(prefs, person, n=5, similarity=sim_pearson):
    '''返回prefs字典中与person最相似的n个 '''
    scores=[(similarity(prefs, person, other), other)
                for other in prefs if other!=person]
    scores.sort()
    scores.reverse()
    return scores[0:n]

def getRecommendations(prefs, person, similarity=sim_pearson):
    '''利用prefs中其它人的评价与相关系数进行加权平均，为person提供建议'''
    totals={}
    simSums={}

    for other in prefs:
        if other==person: continue  #不与自己做比较
        sim=similarity(prefs,person,other)

        if sim<=0: continue     #忽略相似度小于等于零的情况
        for item in prefs[other]:
            if item not in prefs[person] or prefs[person][item]==0:
                totals.setdefault(item,0)
                totals[item]+=prefs[other][item]*sim
                simSums.setdefault(item,0)
                simSums[item]+=sim

    rankings=[(total/simSums[item],item) for item,total in totals.items()]

    rankings.sort()
    rankings.reverse()
    return rankings

def loadMovieLens(path='F:/CI/2/ml-100k'):
    movies={} #movies = {movie-id:movie-name}

    for line in open(path + '/u.item',errors='ignore'):
        (id, title) = line.split('|')[0:2]
        movies[id] = title

    prefs = {} #prefs = {user:{movie-name:rating,},}
    for line in open(path + '/u.data'):
        (user, movieid, rating, ts) = line.split('\t')  #ts:评价时间
        prefs.setdefault(user, {})
        prefs[user][movies[movieid]] = float(rating)
    return prefs

def transformPrefs(prefs):
    result = {}
    for person in prefs:
        for item in prefs[person]:
            result.setdefault(item, {})
            result[item][person] = prefs[person][item]
    return result

if __name__ == '__main__':
    print(sim_pearson(critics,'Lisa Rose','Gene Seymour'))
    print(getRecommendations(critics,'Toby'))
    p = loadMovieLens()
    #print(p['87'])
    print(getRecommendations(p,'87')[0:30])
