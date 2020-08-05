import os
import pandas as pd
import PyPDF2
import re
import scrapy

from PyPDF2 import PdfFileReader
from scrapy.http import Request


class GetChemicalNamesSpider(scrapy.Spider):
    name = 'get_chemical_names'
    headers = {
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'x-client-data': 'CIi2yQEIo7bJAQjBtskBCKmdygEIjqzKAQiGtcoBCP68ygEI58jKAQi0y8oB',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'en-US,en;q=0.9',
    }

    os.system('rm -f output/*.pdf')

    # excel_data = pd.read_excel('sample.min.xlsx')
    excel_data = pd.read_excel('sample.xlsx')
    urls = []
    for url in excel_data['URL']:
        urls.append(url.strip())

    def start_requests(self):
        # Access each URL in the self.urls list
        for url in self.urls:
            yield Request(url, callback=self.parse, headers=self.headers)
        
    def parse(self, response):
        if response.body:
            body = response.body.decode("utf-8", errors="ignore")
            if body.startswith('%PDF'):
                (filename, body) = self._read_pdf(response)
                yield self._parse_pdf_content(response.url, filename)
        else:
            print(f"ERROR - {response.url} download fail")

    # -------------- Helper Methods --------------#
    def _parse_pdf_content(self, url, filename):
        chemical_name = None
        numericals = []
        
        with open(filename, 'rb') as rfile:
            pdf = PdfFileReader(rfile)
            chemical_name = pdf.getDocumentInfo().title
            page_content = pdf.getPage(0).extractText()
            if re.search(r'\[[\d+-?]+\]', page_content):
                numericals = re.findall(r'\[[\d+-?]+\]', page_content)
        
        return {
            'url': url,
            'chemical_name': chemical_name if chemical_name else 'NA',
            'numericals': numericals if numericals else 'NA'
        }
    
    def _read_pdf(self, response):
        body = ""
        pdf_number = response.url.split("/")[-1].split('.')[0]
        filename = f'output/response-{pdf_number}.pdf'
        file = open(filename, 'wb')
        file.write(response.body)
        file.close()

        # creating a pdf file object
        pdfFileObj = open(filename, 'rb')
        # creating a pdf reader object
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        # Go through all the pages and extract text
        for page_num in range(pdfReader.numPages):
            # creating a page object
            pageObj = pdfReader.getPage(page_num)
            # extracting text from page
            body += pageObj.extractText()
        return (filename, body)