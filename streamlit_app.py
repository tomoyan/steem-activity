import streamlit as st
import requests
from datetime import datetime, timedelta
from _steem import get_steem

# PAGE_CONFIG
st.set_page_config(
    page_title="Japan Steemit Community",
    page_icon="random",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title('Steemit User Activity')


def get_request(url):
    # get request to sds.steemworld.org
    # return json result
    json_data = {}

    response = requests.get(url)
    if response:
        json_data = response.json()

    return json_data


@st.cache(ttl=3600)
def get_community_subs():
    subscribers = []
    url = (
        'https://sds.steemworld.org'
        '/communities_api'
        '/getCommunitySubscribers'
        '/hive-161179'
    )
    json_data = get_request(url)
    subscribers = json_data['result']

    return subscribers


input_1, input_2 = st.columns(2)
with input_1:
    username = st.selectbox(
        'Select username:',
        ('', *get_community_subs()),
        index=0)
with input_2:
    duration = st.number_input(
        'duration (1 - 30 days):',
        min_value=1,
        max_value=30,
        value=7)

if not username or not duration:
    st.stop()


@st.cache(ttl=3600)
def get_timestamps(duration):
    timestamps = []

    for i in range(0, duration):
        today = datetime.now()
        today = today.replace(minute=0, hour=0, second=0, microsecond=0)

        start = today - timedelta(days=i + 1)
        stop = today - timedelta(days=i)
        timestamps.append({
            'start_date': start.strftime("%Y/%m/%d"),
            'stop_date': stop.strftime("%Y/%m/%d"),
            'start': int(start.timestamp()),
            'stop': int(stop.timestamp())})

    return timestamps


@st.cache(ttl=3600)
def get_account_info(username):
    result = {}
    STEEM = get_steem()

    url = (
        'https://sds.steemworld.org'
        '/accounts_api'
        '/getAccount'
        f'/{username}'
        '/witness_votes,proxy,'
        'vesting_shares,delegated_vesting_shares,'
        'voting_power'
    )

    json_data = get_request(url)
    if not json_data['result']:
        return result

    result = json_data['result']
    result['voting_power'] = float(f"{result['voting_power']*0.01:.2f}")
    result['total_sp'] = STEEM.vests_to_sp(result['vesting_shares'])
    result['total_sp'] = float(f"{result['total_sp']:.2f}")
    result['effective_sp'] = STEEM.vests_to_sp(
        result['vesting_shares'] - result['delegated_vesting_shares'])
    result['effective_sp'] = float(f"{result['effective_sp']:.2f}")

    return result


timestamps = get_timestamps(duration)
account_info = get_account_info(username)

if not account_info:
    st.error('Account Not Found')
    st.stop()


def get_vote_count(username, start, stop):
    count = 0
    url = (
        'https://sds.steemworld.org'
        '/account_history_api'
        '/getHistoryByOpTypesTime'
        f'/{username}'
        '/vote'
        f'/{start}-{stop}'
    )
    json_data = get_request(url)
    rows = json_data['result']['rows']

    for r in rows:
        # r[6] = op data
        if r[6][1]['voter'] == username:
            count += 1

    return count


@st.cache(ttl=3600)
def vote_history(username, timestamps):
    result = []
    for ts in timestamps:
        count = get_vote_count(username, ts['start'], ts['stop'])
        result.append(f"{ts['start_date']}: {count} times")

    # st.write(result)
    return result


@st.cache(ttl=3600)
def get_recent_posts(username, limit):
    posts = []
    url = (
        'https://sds.steemworld.org'
        '/posts_api'
        '/getRootPostsByAuthor'
        f'/{username}'
        '/false'
        '/created,title'
        f'/{limit}'
    )

    json_data = get_request(url)
    if not json_data['result']:
        return posts

    # posts = json_data['result']['rows']
    for row in json_data['result']['rows']:
        date = datetime.fromtimestamp(row[0]).strftime('%Y-%m-%d')
        posts.append(f'{date}: {row[1]}')

    posts.reverse()
    return posts


# Display data
name, avatar = st.columns(2)
# column 1
name.subheader(f"@{username}'s stats")

# column 2
avatar_img = f'https://steemitimages.com/u/{username}/avatar'
avatar.image(avatar_img)

col1, col2, col3 = st.columns(3)
col1.metric('Total SP', f"{account_info['total_sp']:,.2f} SP")
col2.metric('Effective SP', f"{account_info['effective_sp']:,.2f} SP")
col3.metric("Voting Power", f"{account_info['voting_power']} %")

witness_tomoyan, witness_yasu, proxy = st.columns(3)
# col 1 witness_tomoyan check
with witness_tomoyan:
    st.caption('tomoyan.witness vote')
    if 'tomoyan.witness' in account_info['witness_votes']:
        st.info('tomoyan.witness ✔️')
    else:
        st.error('tomoyan.witness 😢')
# col 2 witness_yasu check
with witness_yasu:
    st.caption('yasu.witness vote')
    if 'yasu.witness' in account_info['witness_votes']:
        st.info('yasu.witness ✔️')
    else:
        st.error('yasu.witness 😢')
# col 3 proxy check
with proxy:
    st.caption('proxy vote')
    if not account_info['proxy']:
        st.info('None')
    elif account_info['proxy'] in ['tomoyan.witness', 'yasu.witness']:
        st.info(f"{account_info['proxy']} ✔️")
    else:
        st.error(f"{account_info['proxy']} 😢")


vote_col, post_col = st.columns(2)
with vote_col:
    votes = vote_history(username, timestamps)
    st.subheader('Upvote Counts')
    st.dataframe(votes)

with post_col:
    st.subheader('Recent Posts')
    posts = get_recent_posts(username, duration)
    st.table(posts)
