from crawl4ai import WebCrawler
import requests
import xml.etree.ElementTree as ET
from tqdm import tqdm
import pandas as pd

def fetch_sitemap_urls(sitemap_url):
    # Send a GET request to the sitemap URL
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    response = requests.get(sitemap_url, headers=headers)
    response.raise_for_status()  # Raises an HTTPError for bad responses

    # Parse the XML content of the sitemap
    root = ET.fromstring(response.content)

    # Extract and return the URLs found in the sitemap
    urls = [url.text for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    return urls

urls = fetch_sitemap_urls("https://marclou.beehiiv.com/sitemap.xml")

# Create an instance of WebCrawler
crawler = WebCrawler()

# Warm up the crawler (load necessary models)
crawler.warmup()

# Create an empty dataframe with the desired columns
frames = []

for url in tqdm(urls):
    result = crawler.run(url=url)

    # Extract the relevant information from the result
    content = result.markdown
    title = result.metadata.get('title', '-')
    url = result.url
    description = result.metadata.get('og:description', '-')

    # Append the extracted information to the dataframe
    df_part = pd.DataFrame({'content': [content], 'title': [title], 'url': [url], 'description': [description]})
    frames.append(df_part)

# Print the dataframe
df = pd.concat(frames)
df.to_csv('MarcLou.csv', index=False)