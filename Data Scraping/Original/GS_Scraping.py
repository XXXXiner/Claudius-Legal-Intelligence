# -*- coding: utf-8 -*-
"""
Created on Thu May 30 13:32:19 2024

@author: Jason
"""

import requests
from bs4 import BeautifulSoup

def get_article_citations(article_title):
    search_url = f'https://scholar.google.com/scholar?hl=en&q={article_title}'
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    output={}
    # Find the first search result
    result = soup.find('div', class_='gs_ri')
    
    if result:
        # Extract the citation count
        citation_info = result.find('div', class_='gs_fl')
        # Extract abstract
        abstract= result.find('div', class_='gs_fma_snp')
        # Extract first author's google shcolar link(if no link, pass to next author)
        author_link = result.find('div', class_='gs_fmaa').find('a', href=True)
        author_url = 'https://scholar.google.com' + author_link['href']
        
        if citation_info:
            citation_text = citation_info.find_all('a')[2].get_text()  # Usually the third link is the citation count
            if 'Cited by' in citation_text:
                citation_count = citation_text.split('Cited by ')[1]
        else:
            return "Citation count not found"
        
        #Output
        output['citation_count'] = citation_count
        output['author_url'] = author_url
        output['abstract'] = abstract
    else:
        return "Paper not found"
    return output

def main():
    article_title = input("Enter the title of the article: ")
    out = get_article_citations(article_title)
    citation_count = out['citation_count']
    author_url= out['author_url'] 
    abstract= out['abstract']
    
    print(f"The article '{article_title}' has been cited {citation_count} times.")
    print(f"Author url: {author_url}")
    print(f"Abstract: {abstract}")
if __name__ == "__main__":
    main()