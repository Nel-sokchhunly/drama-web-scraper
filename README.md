# drama-web-scraper

## Dramacool drama scraping module
this project is a module that I create to fetch the drama application in Dramacool website
it take in a list of query_title, scraped it and add/update to the MongoDB database

### How it function
This module has a main function **Job()** and is being called every hour using [Schedule](https://schedule.readthedocs.io/en/stable/) library.
the function **Job()** connect to the MongoDB dramabase and form a set of query_title from the query_title fields in every user and scraped from the dramacool website one by one using **Scraper()** function. Once it run through all the tile in a list of query_title, it will add/update each individual into the **MongoDB** database.

##### How to get query_title
Url : `https://www2.dramacool.sk/drama-detail/us-that-year` then the query_title would be `us-that-year` 

**this only work with this url only**

#### Scraper()
this function take in a query_title as `Scraper(drama_title)` and return an object 
`
{
    'title',
    'query_title',
    'other_name',
    'image_info',
    'description',
    'status'',
    'genre',
    'trailer_embed_link',
    'episodes',
    'last_updated',
}
`
