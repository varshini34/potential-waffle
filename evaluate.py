#Dependencies
import pandas as pd
import numpy as np
import tensorflow as tf
import itertools
import matplotlib.pyplot as plt
import time

from envs import OfflineEnv
from recommender import DRRAgent

import os

ROOT_DIR = os.getcwd()
DATA_DIR = os.path.join(ROOT_DIR, 'ml-1m/')
STATE_SIZE = 10

def evaluate(recommender, env, top_k=False):

        recommender.load_model('/home/diominor/Workspace/DRR/save_weights/actor_50000.h5', '/home/diominor/Workspace/DRR/save_weights/critic_50000.h5')

        # episodic reward 리셋
        episode_reward = 0
        correct_count = 0
        steps = 0
        # Environment 리셋
        user_id, items_ids, done = env.reset()
        print(f'user_id : {user_id}, rated_items_length:{len(env.user_items)}')
        print('items : \n', np.array(env.get_items_names(items_ids)))
        
        while not done:
            
            # Observe current state & Find action
            ## Embedding 해주기
            user_id = tf.convert_to_tensor(user_id)
            items_ids = tf.convert_to_tensor(items_ids)
            user_eb, items_eb = recommender.actor.embedding_network(user_id, items_ids)
            user_eb = tf.reshape(user_eb, (1,1, *user_eb.shape))
            items_eb = tf.reshape(items_eb, (1,*items_eb.shape))
            ## Action(ranking score) 출력
            action, _ = recommender.actor.network(user_eb, items_eb)
            ## Item 추천
            recommended_item = recommender.actor.recommend_item(action, env.recommended_items, top_k=top_k, is_test=True)
            print(f'recommended items ids : {recommended_item}')
            print(f'recommened items : \n {np.array(env.get_items_names(recommended_item), dtype=object)}')
            # Calculate reward & observe new state (in env)
            ## Step
            next_items_ids, reward, done, _ = env.step(recommended_item, top_k=top_k)
            items_ids = next_items_ids
            episode_reward += reward
            steps += 1
            if reward > 0:
                correct_count += 1
                print('GOT IT!!!!')
            print()  

        print(f'precision : {correct_count/steps}, episode_reward : {episode_reward}')
        print()

if __name__ == "__main__":

    print('Data loading...')

    #Loading datasets
    ratings_list = [i.strip().split("::") for i in open(os.path.join(DATA_DIR,'ratings.dat'), 'r').readlines()]
    users_list = [i.strip().split("::") for i in open(os.path.join(DATA_DIR,'users.dat'), 'r').readlines()]
    movies_list = [i.strip().split("::") for i in open(os.path.join(DATA_DIR,'movies.dat'),encoding='latin-1').readlines()]
    ratings_df = pd.DataFrame(ratings_list, columns = ['UserID', 'MovieID', 'Rating', 'Timestamp'], dtype = np.uint32)
    movies_df = pd.DataFrame(movies_list, columns = ['MovieID', 'Title', 'Genres'])
    movies_df['MovieID'] = movies_df['MovieID'].apply(pd.to_numeric)

    print("Data loading complete!")
    print("Data preprocessing...")

    # 영화 id를 영화 제목으로
    movies_id_to_movies = {movie[0]: movie[1:] for movie in movies_list}
    ratings_df = ratings_df.applymap(int)

    # 유저별로 본 영화들 순서대로 정리
    users_dict = {user : [] for user in set(ratings_df["UserID"])}

    # 시간 순으로 정렬하기
    ratings_df = ratings_df.sort_values(by='Timestamp', ascending=True)

    # 유저 딕셔너리에 (영화, 평점)쌍 넣기
    ratings_df_gen = ratings_df.iterrows()
    for data in ratings_df_gen:
        users_dict[data[1]['UserID']].append((data[1]['MovieID'], data[1]['Rating']))

    # 각 유저별 영화 히스토리 길이
    users_history_lens = [len(users_dict[u]) for u in set(ratings_df["UserID"])]

    users_num = max(ratings_df["UserID"])+1
    items_num = max(ratings_df["MovieID"])+1

    # Evaluating setting
    eval_users_num = int(users_num * 0.2)
    eval_items_num = items_num
    eval_users_dict = {k:users_dict[k] for k in range(users_num-eval_users_num, users_num)}
    eval_users_history_lens = users_history_lens[-eval_users_num:]

    print('DONE!')
    time.sleep(2)

    env = OfflineEnv(eval_users_dict, eval_users_history_lens, movies_id_to_movies, STATE_SIZE)
    recommender = DRRAgent(env, users_num, items_num, STATE_SIZE)
    recommender.actor.build_networks()
    recommender.critic.build_networks()
    evaluate(recommender, env, 10)
