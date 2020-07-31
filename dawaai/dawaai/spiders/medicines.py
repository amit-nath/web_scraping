# -*- coding: utf-8 -*-
import scrapy
from scrapy.http.request import Request
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.exceptions import CloseSpider

class MedicinesSpider(CrawlSpider):
    name = 'medicines'
    allowed_domains = ['dawaai.pk']
    start_urls = ['https://dawaai.pk/']
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'

    rules = (
        Rule(LinkExtractor(restrict_css="li:nth-child(3) a", deny=r'/faq|/blog', ), follow=True, process_request='set_user_agent'),
        Rule(LinkExtractor(restrict_css=".view-test-main"), callback='parse_item', follow=True, process_request='set_user_agent'),
    )

    def set_user_agent(self, request):
        request.headers['User-Agent'] = self.user_agent
        return request

    def parse_item(self, response):
        if response.css('h1::text'):
            name = response.css('h1::text').get()
        else:
            name = 'NA'
        
        if response.css('.per_stripp::text'):
            discounted_price = response.css('.per_stripp::text').get().strip()
        elif response.css("#price_product::text").get().strip():
            discounted_price = response.css("#price_product::text").get().strip()
        else:
            discounted_price = 'NA'
        
        if response.css('.pack_price::text'):
            actual_price = response.css('.pack_price::text').get().strip()
        elif response.css('.cut-price::text'):
            actual_price = response.css('.cut-price::text').get().strip()
        else:
            actual_price = 'NA'
        
        if response.css('.pharma-company a::text'):
            manufacturer = response.css('.pharma-company a::text').get()
        elif response.xpath('//div[@class="product-desc-right"]//a/text()'):
            manufacturer = response.xpath('//div[@class="product-desc-right"]//a/text()').get().strip()
        else:
            manufacturer = 'NA'
        
        yield {
            'Name': name,
            'Actual Price': actual_price,
            'Discounted Price': discounted_price,
            'Manufacturer': manufacturer,
            'Medicine URL': response.url
        }

    # def load_more(self, resp):
    #     next_page = 1
    #     while resp.status_code == 200:
    #         next_page_url = response.urljoin(f'category/getmore/459/{next_page}/0/0/0/0/0/0')
    #         yield Request(next_page_url, callback=self.parse_item, headers={'User-Agent': self.user_agent})


