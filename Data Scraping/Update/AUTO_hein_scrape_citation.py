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
import pandas as pd



def download(args):
    # Change the first letter variable to be the first letter of the journal you want
    journal_name = args.journal_name
    # tab_index = ord(journal_name[0].lower()) - ord('a') + 1
    first_letter = driver.find_element(By.LINK_TEXT, journal_name[0].upper())
    # first_letter = driver.find_element(By.XPATH, '//*[@id="headerWrapper"]/div/a[{}]'.format(tab_index))
    first_letter.click()

    # Go to the page of this journal
    journal = driver.find_element(By.LINK_TEXT, journal_name)
    journal.click()


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
                time.sleep(3)

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
                    time.sleep(3)

                    cited_by_articles_count = driver.find_element(By.ID, 'cite_counts')
                    cited_by_articles_count = int(cited_by_articles_count.text)
                    article_data["citedby_articles"] = cited_by_articles_count

                    cited_by_cases_count = driver.find_element(By.ID, 'cite_counts2')
                    cited_by_cases_count = int(cited_by_cases_count.text)
                    article_data["citedby_cases"] = cited_by_cases_count
                    
                    cited_by_ALI_count = driver.find_element(By.ID, 'cite_counts2ali')
                    cited_by_ALI_count = int(cited_by_ALI_count.text)
                    article_data["citedby_ALI"] = cited_by_ALI_count

                    accessed_times_count = driver.find_element(By.ID, 'cite_counts3')
                    accessed_times_count = int(accessed_times_count.text)
                    article_data["accessed_times"] = accessed_times_count

                    # cites = driver.find_element(By.CLASS_NAME,'citation_icon')
                    # cites.click()
                    # cites_bluebook = driver.find_element(By.ID, 'hn_cit4').text
                    # article_data["cites_bluebook"] = cites_bluebook
                    # close = driver.find_element(By.CLASS_NAME,'fa-times-circle')
                    # close.click()

                    
                    citation.click()
                    time.sleep(3)
                except Exception as e:
                    article_data["citedby_articles"] = 'N/A'
                    article_data["citedby_cases"] = "N/A"
                    article_data["citedby_ALI"] = "N/A"
                    article_data["accessed_times"] = "N/A"
                    # article_data["cites_bluebook"] =   'N/A'
                    # article_data["citing_articles"] = []
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
            time.sleep(5)
    except Exception as e:
        print(e)
        print('*'*20)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--journal_name', type=str, default="Alabama Law Review")
    parser.add_argument('--journal_abbrev', type=str, default="bamalr")
    parser.add_argument('--start_vol', type=int, default=52) # scraping starts at this volume number
    parser.add_argument('--end_vol', type=int, default=74)   # scraping ends at this volume number
    parser.add_argument('--headless', action='store_true')  # scrape without opening browser window
    
    args = parser.parse_args()


    LANDING_URL = "https://heinonline.org.revproxy.brown.edu/HOL/Welcome"  # url for log in page
    LOG_IN_WAIT_TIME = 40                                # wait time to allow us to enter log in info, unit: second
    OUTPUT_DIR = './'                                   # output directory

    # skip the article if its title starts with one of these stopwords
    STOPWORDS = ['table of contents', 'title page', 'index to volume']

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

    # Go to log in page and manually enter log in info
    landing_url = LANDING_URL
    driver.get(landing_url)
    time.sleep(LOG_IN_WAIT_TIME)

    journal_lib = driver.find_element(By.LINK_TEXT, "Law Journal Library")
    journal_lib.click()
    law_journal_lib = driver.current_url


    data = pd.read_excel("all journals in database.xlsx")
    #filter the journals that are not yet scraped and abbrev is not NAN
    data = data[data["Progress"] != "Scraped"]
    data = data[data["Abbrev"].notna()]

    # read the data row by row
    for index, row in data.iterrows():
        try:
            args.journal_name = row["Journal"].strip()
            args.journal_abbrev = row["Abbrev"]
            args.start_vol = int(row["Start"])
            args.end_vol = int(row["End"])
            print(args.journal_name)
            print(args.journal_abbrev)
            print(args.start_vol)
            print(args.end_vol)
            download(args)
            driver.get(law_journal_lib)
            data.at[index, "Progress"] = "Scraped"
        except Exception as e:
            print(e)
            print("Error in scraping " + args.journal_name)
            data.at[index, "Progress"] = "Error"
    data.to_excel("Xiner Journals Progress.xlsx", index=False)