from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.select import Select
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import re
import argparse
import os
from urllib.parse import urlparse, parse_qs


LANDING_URL = "https://heinonline.org/HOL/Welcome"  # url for log in page
LOG_IN_WAIT_TIME = 5                                # wait time to allow us to enter log in info, unit: second
OUTPUT_DIR = './'                                   # output directory

# skip the article if its title starts with one of these stopwords
STOPWORDS = ['table of contents', 'title page', 'index to volume']


def download(args):
    service=Service(ChromeDriverManager().install())

    # Options
    chrome_options = Options()

    if args.headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument("start-maximised")
        
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Depending on speed at which browsers load, this implicit wait time may need to be adjusted
    driver.implicitly_wait(5)

    parent = driver.window_handles[0]
    driver.switch_to.window(parent)

    # # Go to log in page and manually enter log in info
    # landing_url = LANDING_URL
    # driver.get(landing_url)
    # time.sleep(LOG_IN_WAIT_TIME)

    # journal_lib = driver.find_element(By.LINK_TEXT, "Law Journal Library")
    # journal_lib.click()

    # Change the first letter variable to be the first letter of the journal you want
    journal_name = args.journal_name
    # # tab_index = ord(journal_name[0].lower()) - ord('a') + 1
    # first_letter = driver.find_element(By.LINK_TEXT, journal_name[0].upper())
    # # first_letter = driver.find_element(By.XPATH, '//*[@id="headerWrapper"]/div/a[{}]'.format(tab_index))
    # first_letter.click()

    # # Go to the page of this journal
    # journal = driver.find_element(By.LINK_TEXT, journal_name)
    # journal.click()

    journal_abbrev = args.journal_abbrev

    LANDING_URL = "https://heinonline.org/HOL/Index?index=journals/{}&collection=journals".format(journal_abbrev)
    landing_url = LANDING_URL
    driver.get(landing_url)
    time.sleep(LOG_IN_WAIT_TIME)



    # List of volumes to be scraped
    vol_number_list=[str(x) for x in range(args.start_vol, args.end_vol + 1)]

    # Data dict for this journal
    data = {}

    # Create output directory
    output_dir = OUTPUT_DIR + args.journal_name + '/'
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # i is volume number
        for vol_num in vol_number_list:
            volume_list = driver.current_url
            volumes=driver.find_elements(By.PARTIAL_LINK_TEXT, vol_num+" ")

            # Volume number = year
            if not volumes:
                volumes=driver.find_elements(By.PARTIAL_LINK_TEXT, vol_num)
            
            print([volume.text for volume in volumes])
            vol = volumes[len(volumes)-1]

            # Check volume number
            true_vol_num = vol.text.split(' ')[0].strip()
            
            # If wrong volume number, log errors
            if vol_num != true_vol_num:
                log_filename = '{}_vol{}_error_wrong_vol_num.txt'.format(journal_name.replace(' ', '_'), vol_num)
                with open(output_dir + log_filename, 'a') as f:
                    f.write(vol_num + '\t' + vol.text)
                    f.write('\n')
                continue

            vol.click()
            data[journal_name]= {vol_num:[]}
            elements = driver.find_elements(By.CLASS_NAME, 'atocpage')

            # List of ids of html elements that correspond to articles
            id_list = [element.get_attribute('id') for element in elements]
            for id in id_list:
                # No link
                if journal_name == "St. John's Law Review" and vol_num == "80" and id == "20":
                    continue
                
                section = driver.find_element(By.XPATH, '//*[@id="'+id+'"]')
                article = section.find_element(By.XPATH, './div/a[1]')
                article.click()
                article_url = driver.current_url
                # article = section.find_element(By.XPATH, './div/a[1]')
                # article.click()
                time.sleep(1)

                # Get entry type
                entry_type = section.find_element(By.XPATH, './i[1]').text
                if entry_type == '':
                    entry_type = 'Article'
                
                # Skip table of contents, title page etc.
                if any(entry_type.lower().startswith(stopword) for stopword in STOPWORDS):
                    continue
                
                # Skip issues
                pattern = re.compile("issue\ \d+")
                if bool(re.match(pattern, entry_type.lower())):
                    continue

                # Skip non articles
                if entry_type != 'Article':
                    continue

                # Data dict for this article
                article_data = {}
                

                # Get title
                # Title is the textContent of the second child node of the section element
                title = driver.execute_script("return arguments[0].childNodes[1].textContent.trim();", section)
                article_data["title"] = title
                article_data["entry_type"] = entry_type

                print('volume: ' + str(vol_num) + '; ' + entry_type + '; ' + str(title))

                # Get authors
                authors=None
                if(len(section.find_elements(By.XPATH,'./a'))>1):
                    title_author = section.text.split("\n")
                    authors = title_author[1].split(";")
                    authors = [author.strip() for author in authors]
                article_data["authors"] = authors

                # Get date and url
                article_data["url"] = article_url



                # Get citation info
                try:
                    citation = driver.find_element(By.CLASS_NAME,'scholarcheck_icon')
                    citation.click()
                    cited_by_articles_count = driver.find_element(By.ID, 'cite_counts')
                    cited_by_articles_count = int(cited_by_articles_count.text)
                    article_data["citedby_articles"] = cited_by_articles_count

                    citing_articles = []
                    if cited_by_articles_count == 0:
                        article_data["citing_articles"] = citing_articles
                    else:
                        cited_by_articles_link = driver.find_element(By.ID,'cite_countsd')
                        cited_by_articles_link.click()

                        time.sleep(1)
                        scroll_count = 0
                        while "No More Results" not in driver.page_source:
                            # Scroll down
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            print('Scrolling...' + str(scroll_count))
                            scroll_count += 1
                            time.sleep(15)

                        
                        # # Get scroll height after first time page load
                        # last_height = driver.execute_script("return document.body.scrollHeight")
                        # while True:
                        #     # Scroll down to bottom
                        #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        #     # Wait to load page / use a better technique like `waitforpageload` etc., if possible
                        #     time.sleep(5)
                        #     # Calculate new scroll height and compare with last scroll height
                        #     new_height = driver.execute_script("return document.body.scrollHeight")
                        #     if new_height == last_height:
                        #         break
                        #     last_height = new_height

                        time.sleep(2)
                        search_results = driver.find_elements(By.XPATH, "//div[contains(@class, 'lucene_search_result_b')]")

                        for search_result in search_results:
                            try:
                                citing_article_name = search_result.find_element(By.XPATH, "./dt[1]").text
                            except:
                                citing_article_name = 'N/A'
                            
                            try:
                                citing_article_journal = search_result.find_element(By.XPATH, "./dt[3]").text
                            except:
                                citing_article_journal = 'N/A'
                            
                            try:
                                citing_article_authors = search_result.find_element(By.XPATH, "./dt[4]").text
                            except:
                                citing_article_authors = 'N/A'
                            
                            try:
                                citing_article_ref = search_result.find_element(By.XPATH, "./dt[6]").text
                            except:
                                citing_article_ref = 'citing_article_ref'
                            
                            citing_articles.append(
                                {
                                    'citing_article_name': citing_article_name,
                                    'citing_article_journal': citing_article_journal,
                                    'citing_article_authors': citing_article_authors,
                                    'citing_article_ref': citing_article_ref
                                }
                            )

                        article_data["citing_articles"] = citing_articles
                        driver.back()
                    
                    citation.click()
                    time.sleep(1)
                except Exception as e:
                    article_data["citedby_articles"] = 'N/A'
                    article_data["citing_articles"] = []
                    print("Error: " + article_url)
                    print(e)
                    
                    # Log errors
                    log_filename = '{}_vol{}_error_citation.txt'.format(journal_name.replace(' ', '_'), vol_num)
                    with open(output_dir + log_filename, 'a') as f_error:
                        f_error.write(article_url)
                        f_error.write('\n')

                # Write data dict to json
                data[journal_name][vol_num].append(article_data)
                json_filename = '{}_vol{}.json'.format(journal_name.replace(' ', '_'), vol_num)
                with open(output_dir + json_filename, 'w') as f:
                    json.dump(data, f, indent=4)
                
            # Get back to the volume page
            driver.get(volume_list)
            time.sleep(2)
    except Exception as e:
        print(e)
        print('*'*20)

# Convert html list to dictionary
def html_list_to_dict(html_list):
    result = {}
    for li in html_list.find_all("li", recursive=False):
        key = next(li.stripped_strings)
        html_list = li.find("ol")
        if html_list:
            tmp = html_list_to_dict(html_list)
            if tmp: 
                result[key] = tmp
            else:
                result[key] = None
        else:
            result[key] = None
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--journal_name', type=str)
    parser.add_argument('--journal_abbrev', type=str)
    parser.add_argument('--start_vol', type=int) # scraping starts at this volume number
    parser.add_argument('--end_vol', type=int)   # scraping ends at this volume number
    parser.add_argument('--headless', action='store_true')  # scrape without opening browser window
    
    args = parser.parse_args()

    download(args)