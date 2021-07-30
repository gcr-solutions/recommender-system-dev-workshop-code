import json
import logging
import sys
import urllib

from bs4 import BeautifulSoup
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def process_item(item_text):
    # Ian McKellen (screenplay)
    if "(" in item_text:
        return item_text.split('(')[0].strip()
    return item_text


def find_items(item, type):
    items = "|".join([process_item(item_text.strip()) for item_text in
                      str(item.text).replace(f'{type}s:', "").replace(f'{type}:', "").strip().split("|")[0].split(",")])
    return items


def find_movie_info_by_url(url):
    # https://www.imdb.com/title/tt0113189/?ref_=fn_al_tt_1
    # with urllib.request.urlopen(url) as response:
    #     html = response.read()
    response = requests.get(url)
    html = response.text

    soup = BeautifulSoup(html, 'html.parser')
    title_wrapper = None
    title_bar_wrapper = None
    plot_summary = None
    popularity_items = None
    title_details = None
    try:
        title_wrapper = soup.find("div", {'class': "title_wrapper"})
    except Exception:
        logger.error("Cannot find 'title_wrapper'")

    try:
        title_bar_wrapper = soup.find("div", {'class': "title_bar_wrapper"})
    except Exception:
        logger.error("Cannot find 'title_bar_wrapper'")

    try:
        plot_summary = soup.find("div", {'class': "plot_summary"})
    except Exception:
        logger.error("Cannot find 'plot_summary'")

    try:
        popularity_items = soup.find_all("div", {"class": "titleReviewBarItem"})
    except Exception:
        logger.error("Cannot find 'titleReviewBarItem'")

    try:
        title_details = soup.find("div", {"class": "article", "id": "titleDetails"}).find_all("div",
                                                                                              {"class": "txt-block"})
    except Exception:
        logger.error("Cannot find 'titleDetails'")

    title = "NA"
    year = "NA"
    category_property = "NA"
    country = 'NA'
    level = "NA"

    if title_wrapper:
        year = title_wrapper.find("h1").find("span").find('a').text
        title = title_wrapper.find("h1").text.replace(f'({year})', '').strip()
        subtext = [it.strip() for it in title_wrapper.find("div", {'class': 'subtext'}).text.split("|")]
        level = subtext[0]
        time = subtext[1]
        category_property = "|".join([it.strip() for it in subtext[2].split(",")])
        time_and_country = subtext[3]
        if '(' in time_and_country:
            country = time_and_country.split("(")[1].replace(")", "")
        logger.info(f"title:'{title}', "
                    f"year:'{year}',"
                    f"level:'{level}', "
                    f"category_property:'{category_property}', "
                    f"country:{country}")

    ticket_num = "NA"
    score = "NA"
    if title_bar_wrapper:
        strong = title_bar_wrapper.find("div", {"class": "ratings_wrapper"}) \
            .find("div", {"class": "ratingValue"}).find("strong")[
            'title']
        ratings = strong.split(" ")
        score = ratings[0]
        ticket_num = ratings[3].replace(",", '')

    popularity = 'NA'
    if popularity_items:
        for item in popularity_items:
            if 'Popularity' in item.text:
                popularity = str(item.text).replace("Popularity", "").split("(")[0].strip().replace(",", "")

    logger.info(f"score: {score}, ticket_num: {ticket_num}, popularity: {popularity}")

    director = 'NA'
    writer = 'NA'
    stars = 'NA'

    if plot_summary:
        sum_items = plot_summary.find_all("div", {"class": "credit_summary_item"})
        for it in sum_items:
            if 'Director:' in it.text or 'Directors:' in it.text:
                director = find_items(it, 'Director')
            elif 'Writer:' in it.text or 'Writers:' in it.text:
                writer = find_items(it, 'Writer')
            elif 'Stars:' in it.text or 'Star:' in it.text:
                stars = find_items(it, 'Star')
            else:
                logging.error(it)

        logger.info(f"director: '{director}', writer: '{writer}', stars: '{stars}'")

    language = 'NA'
    if title_details:
        for it in title_details:
            if 'Language:' in it.text:
                language = "|".join([item.strip() for item in str(it.text).replace('Language:', '').split("|")])
    re_val = {
        "title": title,
        "release_year": year,
        "level": level,
        "category_property": category_property,
        "country": country,
        "director": director,
        "writer": writer,
        "stars": stars,
        "score": score,
        "ticket_num": ticket_num,
        "popularity": popularity,
        "language": language
    }
    logging.info(json.dumps(re_val, indent=2))
    return re_val


# url = 'http://www.imdb.com/title/tt0022879/?ref_=fn_al_tt_1'
# find_movie_info_by_url(url)
# sys.exit(0)

# input_file = "./movie_url.csv"
input_file = "./err.txt"

item_id_and_url_list = []

with open(input_file, "r") as input:
    lines = input.readlines()

for line in lines:
    items = line.split(",")
    if len(items) == 2:
        item_id_and_url_list.append((items[0], items[1].strip()))

logging.info("item_id_and_url_list size: {}".format(len(item_id_and_url_list)))

n = 0
total_size = len(item_id_and_url_list)

error_lines = []

item_file = "item2.csv"
with open(item_file, "w") as output:
    for id, url in item_id_and_url_list:
        n = n + 1
        logging.info("{} - {}/{}".format(url, n, total_size))
        try:
            movie_info = find_movie_info_by_url(url)
        except Exception as e:
            logging.error(e)
            error_lines.append("{},{}\n".format(id, url))
            continue

        movie_info['id'] = id
        items = [movie_info['id'],
                 "1",
                 movie_info['title'],
                 movie_info['release_year'],
                 movie_info['director'],
                 movie_info['stars'],
                 movie_info['category_property'],
                 movie_info['language'],
                 movie_info['ticket_num'],
                 movie_info['popularity'],
                 movie_info['score'],
                 movie_info['level'],
                 "0"
                 ]
        line = "_!_".join(items)
        print(line)
        output.write(f"{line.lower()}\n")

logging.info("error count: {}".format(len(error_lines)))
err_file = "err2.txt"
with open(err_file, "w") as output:
    output.writelines(error_lines)
