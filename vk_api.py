import requests
import json
import re
import datetime
import matplotlib.pyplot as plt
from matplotlib import style
style.use('ggplot') 

import sys
non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd) # решение проблемы с emoji в текстах постов и комментариев

def vk_api(method, **kwargs):
    api_request = 'https://api.vk.com/method/'+ method + '?'
    api_request += '&'.join(['{}={}'.format(key, kwargs[key]) for key in kwargs])
    data = json.loads(requests.get(api_request).text)
    
    return data

def group_info():
    group_info = vk_api('groups.getById', group_id='inoekinoclub', v='5.63')
    group_id = group_info['response'][0]['id']
    
    return group_id

def get_posts(group_id):
    posts = []
    item_count = 110

    res_posts = vk_api('wall.get', owner_id=-group_id, v='5.63', count=100)
    posts += res_posts['response']['items']

    while len(posts) < item_count:
        res_posts = vk_api('wall.get', owner_id=-group_id, v='5.63', count=100, offset=len(posts))
        posts += res_posts['response']['items']

        for post in posts:
            posts_text = post['text'].translate(non_bmp_map)
            clean_posts = re.sub('http[^ ]*?($| |,)', '', posts_text).replace('<br>', ' ') # чистим тексты новостей от ссылок

            with open('posts.txt', 'a', encoding='utf-8') as f:
                f.write(str(post['id']) + ' ' + clean_posts + '\n')

    return posts

def get_comments(group_id, posts):
    users_ids = []
    comments_length = []

    data_comments = open('comments.txt', 'a', encoding='utf-8')
    data_graph = open('graph.txt', 'a', encoding='utf-8')
    
    for post in posts:
        res_comments = vk_api('wall.getComments', owner_id=-group_id, count=100, post_id=post['id'])

        for comment in res_comments['response'][1:]:
            uid = comment['from_id']
            uid = str(uid).replace('-', '')
            users_ids.append(uid)
            uids = str(uid) + '\n'

            with open('uids.txt', 'a', encoding='utf-8') as f:
                    f.write(uids)


        c_length = 0
        i = 0

        for comment in res_comments['response'][1:]:
            i += 1
            comments_text = comment['text'].translate(non_bmp_map)
            clean_comments = re.sub('http[^ ]*?($| |,)', '', comments_text) # чистим комментарии от ссылок
            clean_comments = re.sub('\[.*?\]','', clean_comments) # чистим комментарии от имен пользователей, на которых ссылаются авторы комментария, например, [id373769902|Василий]
            clean_comments = clean_comments.replace('/*', '').replace('"', '').replace('<br>', ' ')

            comm_length = len(clean_comments.split())
            if comm_length != None and comm_length != "":
                comments_length.append(comm_length)

            if i == 100:
                res_comments = requests.get('https://api.vk.com/method/wall.getComments?owner_id=-' + str(group_id) + '&count=100&offset=' + str(len(res_comments)) + '&post_id=' + str(post['id']))
                comments = json.loads(res_comments.text)

                c_length += len(clean_comments.split())
                data_comments.write(str(post['id']) + ' ' + clean_comments + '\n')

            else:
                c_length += len(clean_comments.split())
                data_comments.write(str(post['id']) + ' ' + clean_comments + '\n')


        posts_text = post['text'].translate(non_bmp_map)
        clean_posts = re.sub('http[^ ]*?($| |,)', '', posts_text).replace('<br>', ' ')


        if i != 0:
            data_graph.write(str(len(clean_posts.split())) + ' ' + str(round((c_length / i), 0)) + '\n') 
        else:
            print('pass')

    data_comments.close()
    data_graph.close()

    return res_comments, users_ids, comments_length

def make_post_comment():
    posts_x = []
    comments_y = []
    gr_count = 0

    with open('graph.txt', 'r', encoding ='utf-8') as f:
        lines = f.read()
        lines = lines.split()
        for line in lines:
            gr_count += 1
            if gr_count % 2 != 0:
                posts_x.append(line)
            else:
                comments_y.append(line)

    x = [int(post_x) for post_x in posts_x]
    y = [float(comment_y) for comment_y in comments_y]

    plt.bar(x, y)
    plt.title('Соотношение длины постов с длинной комментариев')
    plt.xlabel('Длина постов')
    plt.ylabel('Длина комментариев')
    plt.show()

def get_city(users_ids, comments_length):
    cities = {}

    i = 0 
    for user in users_ids:
        res_users = vk_api('users.get', user_ids=user, fields='city')

        for ucity in res_users['response']:
            if 'city' in ucity: # наличие city вообще
                if ucity['city'] in cities: # наличие city в словаре
                    cities[ucity['city']].append(comments_length[i])
                    i += 1
                else:
                    cities[ucity['city']] = []
                    cities[ucity['city']].append(comments_length[i])
                    i += 1
    # print(cities)
    return cities

def make_city_comment(cities):
    keys = []
    values = []

    for value in cities.values():
        count_comments = round((sum(value) / len(value)), 0)
        values.append(count_comments)

    for key in cities.keys():
        keys.append(key)

    t = [int(k) for k in keys]
    x = range(len(keys))
    y = [float(v) for v in values]
   
    plt.bar(x, y, tick_label=t)
    plt.title('Соотношение городов с длинами комментариев')
    plt.xlabel('Город')
    plt.ylabel('Средняя длина комментария')
    plt.xticks(rotation='vertical')
    plt.show()


def get_age(users_ids, comments_length):
    ages = {}

    i = 0
    for user in users_ids:
        res_users = vk_api('users.get', user_ids=user, fields='bdate')

        if 'bdate' in res_users['response'][0]:
            uage = res_users['response'][0]['bdate']
            age = uage.split('.')

            if len(age) != 3:
                continue

            d = datetime.datetime.now() - datetime.datetime(int(age[2]), int(age[1]), int(age[0]))
            b = d.days // 365.25

            if b not in ages:
                ages[b] = []

            ages[b].append(comments_length[i])
            i += 1

    print(ages)
    return ages

def make_age_comment(ages):
    keys = []
    values = []

    for value in ages.values():
        count_comments = round((sum(value) / len(value)), 0)
        values.append(count_comments)

    for key in ages.keys():
        keys.append(key)

    t = [int(k) for k in keys]
    x = range(len(keys))
    y = [float(v) for v in values]
   
    plt.bar(x, y, tick_label=t)
    plt.title('Соотношение возраста с длинами комментариев')
    plt.xlabel('Возраст')
    plt.ylabel('Средняя длина комментария')
    plt.xticks(rotation='vertical')
    plt.show()


def main():
    info = group_info()
    pst = get_posts(info)
    comm, u, comm_len = get_comments(info, pst)
    make_post_comment()
    c = get_city(u, comm_len)
    mk_city_comment = make_city_comment(c)
    ages = get_age(u, comm_len)
    make_age_comment(ages)

if __name__ == '__main__':
    main()